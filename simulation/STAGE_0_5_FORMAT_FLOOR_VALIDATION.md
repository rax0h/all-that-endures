# Monotonic reader capability floor

This foundation supports upcoming compact authority; it does not yet introduce compact event-ID storage.

Design: new readers accept persistence formats3,4,5; ordinary creation remains3. A commit requiring a newer reader publishes `max(current_format, required_format)` inside the same SQLite transaction as its data. Subsequent paged-only saves cannot downgrade5 to4. Missing, malformed or unsupported current requirements fail closed. A failed transaction must roll back both data and capability floor.

The event-ID worker prepared two tests before hitting a usage limit; root preserved those tests, observed both red, then completed this minimal foundation inline. Red:2 failed,21 deselected in0.27s (missing floor5 support). Green: `PYTHONPATH=.:simulation python -m pytest -q --tb=short simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py`: **51 passed in5.25s**. Publication/open, no downgrade and rollback are directly covered; existing failure/recovery/backup and checked-store tests remain green.

Compact event-ID facade, descriptor conversion/open/save/detach, successor validation and measured history bounds remain pending. No full suite or long run was launched.
