# Same-seat closure verification, iteration 1

This verifies only the R1/R2 fixes from the initial independent review. It is not another independent package review.

Working-tree changes on reviewed HEAD `276d323117cf059f9b6103110e8e6eef083098c2` add a lexical `_OpeningResources` capability, register the captured pin before INSERT/COMMIT, register the session before registry allocation, and fall back to those owned references on failed handoff.

- **R2 closed on inspected source.** The promoted registry-allocation/constructor-return cases pass. Additional independent real-SQLite controls cancel with KeyboardInterrupt and SystemExit immediately after the session is remembered but before `_registry` exists: original cancellation preserved, owned DB closed, zero pins, `_active=False`, `_state='closed'`; missing registry does not break teardown. Evidence: `probe_closure_partial_session.py`, `closure-partial-session.log`, `closure-partial-session-result.json`.
- **R1 original post-COMMIT cancellation leak fixed, but R1 ownership closure remains open.** Recording a candidate before successful INSERT falsely makes it owned if the token already exists. A deterministic repeated UUID negative control against a real pre-existing foreign lease yields SQLite `UNIQUE constraint failed: generation_pins.token`; cleanup then deletes the unchanged foreign lease because its exact store/generation/checksum match. Existing connection stays usable, but its pin row disappears. Evidence: `probe_closure_capture_collision.py`, `closure-capture-collision.log`, `closure-capture-collision-result.json`.

Register after successful INSERT and before COMMIT, or otherwise distinguish a successfully inserted lease from a merely proposed token. Cancellation before registration can roll back the uncommitted insertion; cancellation after registration still has the exact owner for committed cleanup. Preserve the existing foreign pin on duplicate token failure. This is a focused R1 foreign-ownership negative control, not an expanded request to redesign UUID generation.

Independent focused selection: **9 passed, 39 deselected in 13.02s**. Includes both committed-capture cancellation kinds, registry allocation/constructor return, original cancellation teardown, existing foreign private capability rejection, late head change and borrowed connection ownership. Evidence: `closure-focused.log`, `closure-focused.xml`.

Verdict: **R2 closed; R1 needs the small ownership correction above**. Production changes remain read-only from this reviewer.
