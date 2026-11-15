"""Both sides of the historical save-work claim have hash-bound raw graphs."""
import hashlib
import json
from pathlib import Path
import zipfile


def test_baseline_and_candidate_save_counts_have_complete_original_graphs():
    root=Path(__file__).resolve().parents[2]
    base=root/'docs/performance/stage-0-6-current'
    pointers=json.loads((base/'forensic-repair/baseline-save-profile-index.json').read_text())
    expected=json.loads((base/'membership-read-scope/save-work-comparison.json').read_text())
    assert set(pointers)=={'baseline','candidate'}
    for label,pin in pointers.items():
        archive=root/pin['archive']
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==pin['archive_sha256']
        assert set(pin['members'])=={'prepare','commit','acknowledge'}
        with zipfile.ZipFile(archive) as z:
            for phase,member in pin['members'].items():
                data=z.read(member['path'])
                assert hashlib.sha256(data).hexdigest()==member['sha256']
                rows=json.loads(data)
                counts={name:sum(r['calls'] for r in rows if r['function']==name)
                    for name in ('read_identity_membership','_checked_head_row','_visible_record_row')}
                execute={r['calls'] for r in rows if r['function']=='execute'
                    and r['file'].endswith('persistence_sqlite_guard.py')}
                assert len(execute)==1
                counts['sql_execute_calls']=execute.pop()
                assert counts==member['counts']==expected[phase][label]
