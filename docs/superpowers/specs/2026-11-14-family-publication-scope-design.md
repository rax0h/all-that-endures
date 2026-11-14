# Closed family and dependency publication reads

Continue the authorized Stage0.6 performance work after exact hosted-green
b52b86b5/runtime030b9c93. Existing same-engine acknowledgement profile has
6667snapshot starts and3550head checks, including family versions and two complete
backing-dependency validations. Every frozen row and dependency value remains
mandatory evidence; do not remove repeated validation or mint a new certificate.

Selected approach: let FamilySaveParticipant.validate_publication and
BackingDependencyPool.validate_publication own existing checked_read_operation
instead of read_snapshot. This reuses bounded immutable metadata only during one
closed operation. The original row/root/checksum/value checks, frozen-plan and
pin checks, central cold confirmation and acceptance/recovery order remain.
No gameplay callback or iterator crosses the scope; borrowed reads stay ineligible,
writes/rollback invalidate and cleanup runs on exceptions. Default existing256KiB
scope cap; neither class has a smaller caller-configured transient catalog budget.

Alternatives: removing dependency's second validation needs new custody evidence;
publication-wide proofs touch larger recovery boundaries. Neither is justified by
this isolated investigation. Keep the existing established scope implementation.

Prove native work bound with exact save/reopen, missing/corrupt rows, borrowed read,
exception cleanup, frozen-plan/pin rejection and recovery tests. One independent
whole-package review, all findings including Minors resolved. Raw pinned A-B/B-A
whole-save evidence decides promotion; lower work counts alone are insufficient.
No mature, main/default or endurance activation. Same qualified313 runtime and
immutable small input, independently bounded disposable trials only.
