"""One durable continuation stage per process, with immutable retained inputs."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import open_lazy_world_session
import persistence_p5_long_validation as p5
from simulation import continuation_receipts as r


def _phase(name, **details):
    try:
        print(json.dumps(dict(phase=name, **details), sort_keys=True), flush=True)
    except (OSError, ValueError):
        pass  # Diagnostics never define whether an immutable result exists.


@contextmanager
def _measure(metrics, name):
    started, cpu = time.monotonic(), time.process_time()
    _phase(name+'_started')
    try:
        yield
    finally:
        row = dict(wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu)
        metrics['phases'][name] = row
        _phase(name+'_finished', **row)


def _inventory(directory, members):
    directory = Path(directory)
    if (directory.is_symlink() or not directory.is_dir()
            or {p.name for p in directory.iterdir()} != set(members)
            or any(p.is_symlink() or not p.is_file() for p in directory.iterdir())):
        raise ValueError('unexpected input bundle members')


def _unchanged(directory, expected):
    _inventory(directory, expected)
    if any(r.file_hash(Path(directory)/name) != digest for name, digest in expected.items()):
        raise ValueError('stage changed retained input')


def _check_session(session, authority, year, generation):
    version = session.store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()
    if (version is None or int(version[0]) != 6 or session.world.year != year
            or session.world.seed != authority.source_config['seed']
            or session.pin.captured_head != generation
            or session.store.store_identity != authority.store_identity):
        raise ValueError('opened saved world year/generation/identity/format mismatch')


def _new_destination(path):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ValueError('symlink output directory')
    return path


def _publish_bundle(stage, destination):
    """Closed files only. A partial local directory never authenticates as CI output."""
    destination.mkdir()
    try:
        for name in ('candidate.sqlite', 'checkpoint.json', 'save.json'):
            with (stage/name).open('rb') as stream:
                os.fsync(stream.fileno())
            os.link(stage/name, destination/name)
        r.fsync_dir(destination)
        r.fsync_dir(destination.parent)
    except BaseException:
        shutil.rmtree(destination)
        raise


def _save_input(input_bundle, authority, year, predecessor):
    original = r.validate_original(input_bundle/'checkpoint.json', authority)
    years = authority.source_config['milestones']
    r.integer(year, 'save milestone')
    if year not in years:
        raise ValueError('unexpected save milestone')
    if year == years[0]:
        _inventory(input_bundle, {'checkpoint.json', 'p5-long-complete.sqlite'})
        if not r.same(predecessor, dict(kind='publication',artifact=authority.publication.to_dict())):
            raise ValueError('bootstrap predecessor mismatch')
        db = input_bundle/'p5-long-complete.sqlite'
        if db.stat().st_size != authority.published_database_bytes or r.file_hash(db) != authority.published_database_sha256:
            raise ValueError('published source database differs')
        expected = {'checkpoint.json':authority.checkpoint_sha256, db.name:authority.published_database_sha256}
        return original, db, authority.bootstrap_generation, expected
    r.exact(predecessor, ('kind','artifact','receipt_sha256','receipt'), 'save predecessor')
    if predecessor['kind'] != 'year-verified':
        raise ValueError('second year requires verified predecessor')
    # The composition validator is supplied by the acceptance stage; the wrapper
    # independently authenticates its ArtifactRef and exact receipt bytes first.
    r.validate_year_acceptance(predecessor['receipt'], authority)
    prior = predecessor['receipt']
    if prior['binding']['year'] != year-1:
        raise ValueError('wrong accepted predecessor year')
    r.match_producer(r.ArtifactRef.from_dict(predecessor['artifact']), prior['producer'], authority)
    r.hexadecimal(predecessor['receipt_sha256'],64,'predecessor receipt hash')
    if r.receipt_hash(prior) != predecessor['receipt_sha256']:
        raise ValueError('predecessor receipt bytes mismatch')
    saved = r.validate_saved(input_bundle,authority=authority,expected_year=year-1,
        expected_predecessor=prior['saved']['predecessor'],producer=prior['saved']['producer'])
    if not r.same(saved, prior['saved']):
        raise ValueError('accepted predecessor differs from saved manifest')
    db = input_bundle/'candidate.sqlite'
    return original, db, saved['generation'], {p.name:r.file_hash(p) for p in input_bundle.iterdir()}


def save_year(input_bundle, destination, *, authority, year, predecessor, producer):
    destination = _new_destination(destination)
    r.validate_producer(producer, 'save')
    input_bundle = Path(input_bundle)
    original, source, previous_generation, retained = _save_input(input_bundle, authority, year, predecessor)
    metrics = dict(phases={}, io={}, working_set={})
    with tempfile.TemporaryDirectory(prefix='.continue-save-', dir=destination.parent) as directory:
        private = Path(directory)
        working = private/'candidate.sqlite'
        with _measure(metrics, 'copy'):
            shutil.copyfile(source, working)
            shutil.copyfile(input_bundle/'checkpoint.json', private/'checkpoint.json')
        with _measure(metrics, 'open'):
            session = open_lazy_world_session(working, rules_id=authority.source_config['rules_id'])
        try:
            _check_session(session, authority, year-1, previous_generation)
            session.store.reset_diagnostics()
            with _measure(metrics, 'simulation'):
                Simulation(session.world).run(1)
            metrics['io']['simulation'] = p5._io(session.store.diagnostics())
            _phase('after_simulation', year=session.world.year)
            before = dict(year=session.world.year, counters=p5._counters(session.world))
            control = original['state']['controls'][str(year)]
            if not r.same(before,dict(year=year,counters=control['counters'])):
                raise ValueError('live simulation counters differ from original control')
            session.store.reset_diagnostics()
            with _measure(metrics, 'save'):
                generation = session.save()
            metrics['io']['save'] = p5._io(session.store.diagnostics())
            after = dict(year=session.world.year, counters=p5._counters(session.world))
            if not r.same(after,before) or generation != previous_generation+1:
                raise ValueError('save changed live year/counters or wrong generation')
            _check_session(session, authority, year, generation)
            metrics['working_set'] = p5._compact_working_set(session.diagnostics())
            _phase('after_save', year=year, generation=generation)
            _phase('before_close')
            with _measure(metrics, 'close'):
                session.close()
            _phase('after_close')
        finally:
            if session._active:
                session.close()
        _phase('before_hash')
        with _measure(metrics, 'hash'):
            size = working.stat().st_size
            if not 0 < size <= authority.output_max_bytes:
                raise ValueError('saved database exceeds output cap')
            digest = r.file_hash(working)
            _unchanged(input_bundle, retained)
        saved = dict(schema=r.SCHEMA,stage='year-saved-unverified',authority=authority.to_dict(),
            producer=producer,previous_year=year-1,year=year,previous_generation=previous_generation,
            generation=generation,store_identity=authority.store_identity,
            database=dict(name='candidate.sqlite',bytes=size,sha256=digest),
            checkpoint=dict(name='checkpoint.json',bytes=authority.checkpoint_bytes,sha256=authority.checkpoint_sha256),
            predecessor=predecessor,live_before=before,live_after=after,metrics=metrics)
        r.validate_save_manifest(saved,authority,original,expected_year=year,
            expected_predecessor=predecessor,producer=producer)
        r.publish_receipt(private/'save.json', saved)
        _phase('before_publish')
        _publish_bundle(private,destination)
    _phase('save_bundle_published',year=year,generation=generation,database=saved['database'],
        save_sha256=r.receipt_hash(saved),checkpoint_sha256=authority.checkpoint_sha256)
    return saved


def _read_saved(saved_bundle, authority, candidate):
    saved = r.load_receipt(saved_bundle/'save.json')
    r.match_producer(candidate,saved.get('producer',{}),authority)
    saved = r.validate_saved(saved_bundle,authority=authority,expected_year=saved.get('year'),
        expected_predecessor=saved.get('predecessor'),producer=saved.get('producer'))
    retained = {'candidate.sqlite':saved['database']['sha256'],
        'checkpoint.json':authority.checkpoint_sha256,'save.json':r.file_hash(saved_bundle/'save.json')}
    return saved,retained


def _observe(saved_bundle, destination, *, authority, candidate, producer, kind, continuation=None, expected_binding=None):
    destination = _new_destination(destination)
    r.validate_producer(producer,kind)
    saved_bundle = Path(saved_bundle)
    saved,retained = _read_saved(saved_bundle,authority,candidate)
    binding = r.saved_binding(saved,candidate,retained['save.json'])
    if expected_binding is not None and not r.same(binding,expected_binding):
        raise ValueError('restore saved candidate differs from verified continuation')
    original = r.validate_original(saved_bundle/'checkpoint.json',authority)
    metrics = dict(phases={},io={},working_set={})
    with tempfile.TemporaryDirectory(prefix='.continue-observe-',dir=destination.parent) as directory:
        working = Path(directory)/'working.sqlite'
        with _measure(metrics,'copy'):
            shutil.copyfile(saved_bundle/'candidate.sqlite',working)
        with _measure(metrics,'open'):
            session = open_lazy_world_session(working,rules_id=authority.source_config['rules_id'])
        try:
            _check_session(session,authority,saved['year'],saved['generation'])
            session.store.reset_diagnostics()
            observation = dict(year=session.world.year,generation=session.pin.captured_head,
                store_identity=session.store.store_identity,counters=p5._counters(session.world))
            with _measure(metrics,kind):
                if kind == 'audit':
                    observation.update(audited_state='saved-reopened',audit=p5._audit(session.world))
                elif kind == 'restore-values':
                    snapshot = json.loads(json.dumps(p5.snapshot(session.world,include_digest=False),sort_keys=True,allow_nan=False))
                    observation.update(restored_state='downloaded-reopened',snapshot=snapshot)
                else:
                    observation['digest'],_ = p5._digest(session.world)
            metrics['io'][kind] = p5._io(session.store.diagnostics())
            _phase('after_'+kind,year=session.world.year,generation=session.pin.captured_head)
            with _measure(metrics,'close'):
                session.close()
        finally:
            try:
                if session._active:
                    session.close()
            finally:
                _unchanged(saved_bundle,retained)
    row = dict(schema=r.SCHEMA,stage=r.VERIFICATION_STAGES[kind],authority=authority.to_dict(),
        producer=producer,binding=binding,observation=observation,metrics=metrics,input_preserved=True,
        original_checkpoint=(saved_bundle/'checkpoint.json').read_text(),saved=saved)
    if continuation is not None:
        row['continuation'] = continuation
    r.validate_verification(row,authority,kind=kind,binding=binding)
    r.publish_receipt(destination,row)
    _phase(kind+'_receipt_published',year=saved['year'])
    return row


def audit_year(saved_bundle,destination,*,authority,candidate,producer):
    return _observe(saved_bundle,destination,authority=authority,candidate=candidate,producer=producer,kind='audit')


def digest_year(saved_bundle,destination,*,authority,candidate,producer):
    return _observe(saved_bundle,destination,authority=authority,candidate=candidate,producer=producer,kind='digest')


def _restore(saved_bundle,destination,*,authority,candidate,producer,continuation,kind):
    r.validate_continuation(continuation,authority)
    binding = continuation['final_binding']
    if not r.same(candidate.to_dict(),binding['candidate']):
        raise ValueError('restore input is not the exact retained continuation artifact')
    return _observe(saved_bundle,destination,authority=authority,candidate=candidate,producer=producer,
        kind=kind,continuation=r.continuation_reference(continuation),expected_binding=binding)


def restore_values(saved_bundle,destination,*,authority,candidate,producer,continuation):
    return _restore(saved_bundle,destination,authority=authority,candidate=candidate,producer=producer,
        continuation=continuation,kind='restore-values')


def restore_digest(saved_bundle,destination,*,authority,candidate,producer,continuation):
    return _restore(saved_bundle,destination,authority=authority,candidate=candidate,producer=producer,
        continuation=continuation,kind='restore-digest')
