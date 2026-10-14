"""Versioned post-run historical truth archive. Never called by Simulation.step."""
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from time import perf_counter
import hashlib
import json
import os
import sqlite3
import tempfile

SCHEMA_VERSION = 2
# Explicit authoritative collections. Runtime indexes/caches are not exported.
COLLECTIONS = {
    'person': 'people', 'household': 'households', 'settlement': 'settlements',
    'property': 'economy.property', 'magic_resource': 'magic_resources.resources',
    'material_lot': 'materials.lots', 'item': 'materials.items',
    'skill': 'skills.skills', 'relationship': 'social.edges',
    'partnership': 'social.partnerships', 'parentage': 'genealogy.parents',
    'claim': 'knowledge.claims', 'belief': 'knowledge.beliefs',
    'practice': 'culture.practices', 'adoption': 'culture.adoption',
    'cultural_institution': 'culture.institutions', 'law': 'culture.laws',
    'community': 'communities.communities', 'membership': 'communities.memberships',
    'transmission': 'transmission.records', 'lineage': 'lineage.nodes',
    'infrastructure': 'infrastructure.assets', 'institution': 'institutions.institutions',
    'institution_branch': 'institutions.branches', 'magic_registration': 'institutions.magic_records',
    'cadet_cohort': 'institutions.cadet_cohorts', 'health_condition': 'health.active',
    'coin_supply': 'currency.minted', 'coin_consumption': 'currency.consumed', 'treasury': 'currency.treasuries', 'notice': 'institutions.notices', 'application': 'institutions.applications',
    'path': 'advancement.paths', 'aspiration': 'magic_resources.aspirations',
    'motive': 'agency.motives', 'soul': 'metaphysics.souls',
    'resurrection_token': 'metaphysics.resurrection_tokens', 'church': 'divinity.churches',
    'god': 'divinity.gods', 'great_astral_being': 'divinity.great_astral_beings',
    'threat': 'threat_ecology.threats', 'conflict': 'warfare.conflicts',
    'inquiry': 'society_accountability.inquiries', 'wallet': 'currency.wallets',
    'ambient_field': 'ambient_magic.fields', 'trade_route': 'trade_routes',
}
COVERAGE = {
    'scope': 'retained records and end-of-run snapshots, not a replay checkpoint',
    'actions': 'only the retained tail (at most 50000); not lifetime memory',
    'relationships': 'legacy symmetric weights and shared event IDs; directional reasons unmodeled',
    'knowledge': 'claim confidence is subjective; claim truth may be unknown',
    'life': 'no invented birthplace, childhood, education or ownership intervals',
    'lineage': 'raw typed refs retained; legacy institution IDs can be ambiguous across registries',
    'expression': 'no language, prose, self-concept or autobiographical memory generated',
    'health': 'active conditions plus onset/recovery events; absence is not invented as a diagnosis',
    'cadets': 'cohort membership/graduation is objective institutional history with physical resource events',
}


def value(x):
    if isinstance(x, Enum): return x.value
    if is_dataclass(x): return {f.name: value(getattr(x, f.name)) for f in fields(x)}
    if isinstance(x, dict):
        if all(isinstance(k, str) for k in x): return {k: value(v) for k, v in sorted(x.items())}
        return {'$map': [[value(k), value(v)] for k, v in sorted(x.items(), key=lambda kv: encode(kv[0]))]}
    if isinstance(x, (tuple, list)): return [value(v) for v in x]
    if isinstance(x, (set, frozenset)): return sorted((value(v) for v in x), key=encode)
    if x is None or isinstance(x, (str, int, float, bool)): return x
    raise TypeError(f'unsupported archive value: {type(x).__name__}')


def encode(x):
    return json.dumps(value(x), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def key(x):
    return str(x) if isinstance(x, (str, int)) else encode(x)


def collection(world, path):
    for component in path.split('.'): world = getattr(world, component)
    return world


DDL = '''
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE records(kind TEXT, id TEXT, payload TEXT NOT NULL, PRIMARY KEY(kind,id));
CREATE TABLE events(id INTEGER PRIMARY KEY, year INTEGER, kind TEXT, layer TEXT, payload TEXT NOT NULL);
CREATE TABLE causes(event INTEGER REFERENCES events(id), cause INTEGER REFERENCES events(id), ordinal INTEGER, PRIMARY KEY(event,ordinal));
CREATE TABLE links(source_kind TEXT, source_id TEXT, relation TEXT, target_kind TEXT, target_id TEXT, ordinal INTEGER);
CREATE INDEX events_year ON events(year,id);
CREATE INDEX events_kind ON events(kind,year,id);
CREATE INDEX cause_reverse ON causes(cause,event);
CREATE INDEX link_source ON links(source_kind,source_id,relation,ordinal);
CREATE INDEX link_target ON links(target_kind,target_id,relation,source_kind,source_id);
'''


def export_archive(world, path, *, digest=None):
    """Atomically create a new archive; refuse overwrite. Timings stay outside bytes.

    Byte determinism is guaranteed for the same SQLite version/settings. The
    logical SHA256 is independent of SQLite layout. digest may reuse a measured
    World.digest from the caller; omitted digest is computed here and timed.
    """
    start = perf_counter()
    path = Path(path)
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.ate-archive-', dir=path.parent)
    os.close(fd)
    logical = hashlib.sha256()
    db = sqlite3.connect(tmp)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript(DDL)
        def insert(table, row):
            db.execute(f'INSERT INTO {table} VALUES ({",".join("?" for _ in row)})', row)
            logical.update(encode([table, row]).encode()); logical.update(b'\n')
        def link(sk, si, relation, tk, ti, ordinal=0):
            if ti is not None: insert('links', (sk, key(si), relation, tk, key(ti), ordinal))
        metadata = {'schema': SCHEMA_VERSION, 'seed': world.seed, 'year': world.year,
                    'world_digest': digest or world.digest(), 'coverage': COVERAGE,
                    'collections': COLLECTIONS}
        for k, v in sorted(metadata.items()): insert('metadata', (k, encode(v)))
        # Insert all event nodes before foreign-key edges; validate chronology.
        for e in sorted(world.events, key=lambda e: e.id):
            insert('events', (e.id, e.year, e.kind, e.layer.value, encode(e)))
        for e in sorted(world.events, key=lambda e: e.id):
            for n, c in enumerate(e.causes):
                if c >= e.id: raise ValueError('non-causal event reference')
                insert('causes', (e.id, c, n))
            for n, actor in enumerate(e.actors): link('event', e.id, 'actor', actor.kind, actor.id, n)
            if e.location: link('event', e.id, 'location', e.location.kind, e.location.id)
        for kind, path_spec in sorted(COLLECTIONS.items()):
            for rid, obj in sorted(collection(world, path_spec).items(), key=lambda kv: key(kv[0])):
                insert('records', (kind, key(rid), encode(obj)))
                d = value(obj)
                if isinstance(d, dict):
                    for f in ('origin_event', 'consumed_event', 'source_event', 'cause_event', 'resolved_event', 'event_id'):
                        if d.get(f) is not None: link(kind, rid, f, 'event', d[f])
                    for f in ('transfers', 'provenance', 'shared_history', 'transformations'):
                        for n, eid in enumerate(d.get(f, [])): link(kind, rid, f, 'event', eid, n)
                    for f in ('person', 'producer', 'craftsperson', 'consumed_by', 'assigned_to'):
                        if d.get(f) is not None: link(kind, rid, f, 'person', d[f])
                    if d.get('owner_kind'): link(kind, rid, 'owner_at_export', d['owner_kind'], d.get('owner_id'))
                    if kind == 'person':
                        link(kind, rid, 'household_at_export', 'household', obj.household)
                        link(kind, rid, 'settlement_at_export', 'settlement', obj.settlement)
                        for n, p in enumerate(obj.parents): link(kind, rid, 'parent', 'person', p, n)
                    if kind == 'relationship':
                        link(kind, rid, 'endpoint', 'person', obj.a, 0); link(kind, rid, 'endpoint', 'person', obj.b, 1)
                    if kind == 'household':
                        for n, pid in enumerate(obj.members): link(kind, rid, 'member_at_export', 'person', pid, n)
                    if kind == 'lineage':
                        # Link to lineage nodes, not a guessed institution registry.
                        for n, parent in enumerate(obj.parents): link(kind, rid, 'lineage_parent', 'lineage', parent, n)
                    if kind == 'item':
                        for n, lot in enumerate(obj.materials): link(kind, rid, 'material', 'material_lot', lot, n)
                    if kind == 'skill':
                        for n, teacher in enumerate(obj.teachers): link(kind, rid, 'teacher', 'person', teacher, n)
                    if kind == 'property':
                        for n, (year, ok, oi, eid) in enumerate(obj.ownership):
                            link(kind, rid, 'recorded_owner', ok, oi, n)
                            link(kind, rid, 'ownership_event', 'event', eid, n)
                    if kind == 'transmission':
                        for side in ('source', 'target'): link(kind, rid, side, getattr(obj, side+'_kind'), getattr(obj, side+'_id'))
                        link(kind, rid, 'transmitted_item', obj.item_kind, obj.item_id)
                    if kind == 'institution_branch':
                        link(kind,rid,'institution','institution',obj.institution)
                        link(kind,rid,'settlement','settlement',obj.settlement)
                    if kind == 'notice':
                        link(kind,rid,'branch','institution_branch',obj.branch)
                    if kind == 'application':
                        link(kind,rid,'branch','institution_branch',obj.branch)
                    if kind == 'cadet_cohort':
                        link(kind,rid,'branch','institution_branch',obj.branch)
                        for n,pid in enumerate(sorted(obj.cadets)):link(kind,rid,'cadet','person',pid,n)
                        for n,pid in enumerate(sorted(obj.graduates)):link(kind,rid,'graduate','person',pid,n)
                    if kind == 'health_condition':
                        link(kind,rid,'person','person',obj.person)
                if kind in ('path', 'aspiration', 'motive', 'soul', 'wallet'):
                    link(kind, rid, 'person', 'person', rid)
                if kind in ('belief', 'membership'):
                    link(kind, rid, 'person', 'person', rid[0])
                    link(kind, rid, 'claim' if kind == 'belief' else 'community', 'claim' if kind == 'belief' else 'community', rid[1])
                if kind == 'partnership':
                    for n, p in enumerate(rid): link(kind, rid, 'partner', 'person', p, n)
                    link(kind, rid, 'formed_event', 'event', obj)
        from .personhood import from_person
        beliefs_by_person = {}
        for (pid, cid), confidence in world.knowledge.beliefs.items():
            beliefs_by_person.setdefault(pid, []).append((cid, confidence))
        for pid, person in sorted(world.people.items()):
            insert('records', ('personhood', key(pid), encode(from_person(person, beliefs_by_person.get(pid, ())))))
            link('personhood', pid, 'person', 'person', pid)
        for n, action in enumerate(world.agency.actions):
            insert('records', ('retained_action', str(n), encode(action)))
            link('retained_action', n, 'person', 'person', action.person)
            link('retained_action', n, 'event_id', 'event', action.event_id)
        missing_events = db.execute('''SELECT COUNT(*) FROM links l LEFT JOIN events e
          ON e.id=CAST(l.target_id AS INTEGER) WHERE l.target_kind='event' AND e.id IS NULL''').fetchone()[0]
        if missing_events: raise ValueError(f'{missing_events} dangling event links')
        db.execute('INSERT INTO metadata VALUES (?,?)', ('logical_sha256', encode(logical.hexdigest())))
        db.commit()
        if db.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('broken event cause')
        db.close()
        # Exclusive publication; never silently overwrite an existing archive.
        os.link(tmp, path)
    finally:
        db.close()
        os.unlink(tmp)
    return {'record': 'archive', 'archive_seconds': perf_counter()-start,
            'archive_bytes': path.stat().st_size, 'logical_sha256': logical.hexdigest(),
            'path': str(path)}


class HistoryArchive:
    """Read-only inspector. Rows are evidence, not inferred autobiography."""
    def __init__(self, path):
        self.db = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)
        self.db.row_factory = sqlite3.Row
        if self.metadata().get('schema') != SCHEMA_VERSION:
            self.close(); raise ValueError('unsupported history archive schema')

    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def metadata(self): return {r['key']: json.loads(r['value']) for r in self.db.execute('SELECT * FROM metadata ORDER BY key')}
    def record(self, kind, rid):
        r = self.db.execute('SELECT payload FROM records WHERE kind=? AND id=?', (kind, key(rid))).fetchone()
        return json.loads(r[0]) if r else None
    def records(self, kind, limit=30, offset=0):
        if not 1 <= limit <= 1000 or offset < 0: raise ValueError('limit must be 1..1000 and offset nonnegative')
        return [{'id': r['id'], 'record': json.loads(r['payload'])} for r in self.db.execute(
            'SELECT id,payload FROM records WHERE kind=? ORDER BY id LIMIT ? OFFSET ?', (kind, limit, offset))]
    def event(self, eid):
        r = self.db.execute('SELECT payload FROM events WHERE id=?', (eid,)).fetchone()
        return json.loads(r[0]) if r else None
    def links(self, kind, rid, incoming=False):
        a, b = ('target_kind', 'target_id') if incoming else ('source_kind', 'source_id')
        return [dict(r) for r in self.db.execute(f'SELECT * FROM links WHERE {a}=? AND {b}=? ORDER BY source_kind,source_id,relation,ordinal,target_kind,target_id', (kind, key(rid)))]
    def timeline(self, kind, rid, first=-1000000, last=1000000, limit=100, offset=0):
        if not 1 <= limit <= 1000 or offset < 0: raise ValueError('limit must be 1..1000 and offset nonnegative')
        return [json.loads(r[0]) for r in self.db.execute('''SELECT DISTINCT e.payload,e.year,e.id FROM links l
          JOIN events e ON e.id=CAST(l.source_id AS INTEGER)
          WHERE l.source_kind='event' AND l.target_kind=? AND l.target_id=? AND e.year BETWEEN ? AND ?
          ORDER BY e.year,e.id LIMIT ? OFFSET ?''', (kind, key(rid), first, last, limit, offset))]
    def causal_chain(self, eid, descendants=False, limit=1000):
        if not 1 <= limit <= 10000: raise ValueError('limit must be 1..10000')
        if self.event(eid) is None: return {'events': [], 'truncated': False, 'unknown': 'event not recorded'}
        source, target = ('cause', 'event') if descendants else ('event', 'cause')
        ids = [r[0] for r in self.db.execute(f'''WITH RECURSIVE walk(id) AS (
          SELECT ? UNION SELECT c.{target} FROM causes c JOIN walk w ON c.{source}=w.id LIMIT ?)
          SELECT id FROM walk ORDER BY id''', (eid, limit+1))]
        return {'events': [self.event(i) for i in ids[:limit]], 'truncated': len(ids)>limit}
    def person(self, pid, limit=100, offset=0):
        p = self.record('person', pid)
        if p is None: return {'unknown': 'person not recorded', 'id': pid}
        incoming = self.links('person', pid, True)
        # Timeline is paginated separately; repeated event payloads are not copied.
        records = sorted({(r['source_kind'], r['source_id']) for r in incoming if r['source_kind'] not in ('event', 'retained_action')})
        return {'person': p, 'snapshot_year': self.metadata()['year'],
                'links': self.links('person', pid),
                'related_records': [{'kind': k, 'id': i, 'record': self.record(k, i)} for k, i in records],
                'timeline': self.timeline('person', pid, limit=limit, offset=offset),
                'timeline_page': {'limit': limit, 'offset': offset}, 'coverage': COVERAGE}
    def provenance(self, kind, rid, limit=1000):
        obj = self.record(kind, rid)
        if obj is None: return {'unknown': 'entity not recorded', 'kind': kind, 'id': rid}
        links = self.links(kind, rid)
        events = sorted({int(r['target_id']) for r in links if r['target_kind']=='event'})
        return {'kind': kind, 'id': rid, 'record': obj, 'links': links,
                'events': [self.event(e) for e in events[:limit]], 'truncated': len(events)>limit,
                'coverage': 'only recorded transfers and origin; use causal_chain for upstream causes'}
