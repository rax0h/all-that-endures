"""The scaling VM guard must enforce total work across short statements."""
import importlib.util
import sqlite3
from pathlib import Path
import pytest


@pytest.mark.parametrize('driver',['run_proof_target_group_scaling.py','run_proof_target_incoming_scaling.py'])
def test_scaling_vm_guard_counts_short_statements_and_interrupts(driver):
 path=Path(__file__).resolve().parents[2]/'.github/tests'/driver
 spec=importlib.util.spec_from_file_location('target_group_scaling',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 guard=module._VMWorkBudget(200);db=sqlite3.connect(':memory:')
 try:
  db.set_progress_handler(guard,1)
  with pytest.raises(sqlite3.OperationalError,match='interrupted'):
   for _ in range(100):db.execute('SELECT 1').fetchone()
  assert guard.steps==201
 finally:db.set_progress_handler(None,0);db.close()
