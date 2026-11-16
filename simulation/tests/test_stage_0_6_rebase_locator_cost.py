"""Private rebase point reads must not scan a namespace for each locator."""
import sqlite3

import pytest

from ate_sim import persistence_lazy_store as lazy
from ate_sim.persistence_proof_world_copy import _bounded_rows


@pytest.mark.parametrize('analyzed', [False, True])
def test_rebase_order_locator_reads_have_linear_work_with_real_indexes(analyzed):
    # A namespace-only covering lookup instead of a unique point read must fail
    # this VM-work bound, even though it returns exactly the same logical rows.
    with sqlite3.connect(':memory:') as db:
        db.executescript('CREATE TABLE query_membership(namespace TEXT, record_key BLOB);' + lazy.P4_DDL)
        count = 1024
        rows = [('people', i.to_bytes(4, 'big'), count-i, 126, None, 'checksum')
                for i in range(count)]
        db.executemany('INSERT INTO lazy_order_versions VALUES (?,?,?,?,?,?)', rows)
        if analyzed:
            db.execute('ANALYZE')
        work = 0
        def progress():
            nonlocal work
            work += 1000
            return int(work > count * 128)
        db.set_progress_handler(progress, 1000)
        try:
            actual = list(_bounded_rows(db, 'lazy_order_versions',
                                       ('namespace', 'typed_key'),
                                       ('namespace', 'typed_key', 'ordinal')))
        finally:
            db.set_progress_handler(None, 0)
        assert actual == [('people', i.to_bytes(4, 'big'), count-i) for i in range(count)]
