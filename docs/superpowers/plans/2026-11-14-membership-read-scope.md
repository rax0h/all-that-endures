# Exact membership read scope Implementation Plan

> Execute inline via superpowers:executing-plans; one independent whole-package review.

**Goal:** avoid repeated operational metadata checks within one exact identity-path lookup.
**Architecture:** existing checked_read_operation replaces this method's read_snapshot, budget min(256KiB,self.byte_limit//6), retaining every root/source/forward check.
**Tech Stack:** existing Python/SQLite, qualified313.
**Spec:** docs/superpowers/specs/2026-11-14-membership-read-scope-design.md

## Global Constraints
- Exact source/root/forward agreement, bounded lifetime and original absence semantics.
- Same qualified runtime and immutable input via disposable copies.
- No mature/default/main/endurance; one hosted gate only for retained change.

## Review Focus
- Borrowed/read/write/rollback and callback/codec/lease drift preserve refusal.
- Source/witness loss cannot create a false absent/new-owner result.
- Root/forward corruption after previous successful lookup rejects.
- Tiny configured catalog budget honored and scope cleaned after exceptions.
- Presence, absent path, hash collision and stale pins keep previous behavior.

### Task1: closed point read and complete operation acceptance

Files: persistence_lazy_identity_catalog.py; new tests/test_stage_0_6_membership_read_scope.py; membership-read-scope/ evidence. Interface read_identity_membership(pin,owner,path) unchanged: int|None or raise.

- [x] Generic/native lookup metadata-work RED for presence and absence.
- [x] Minimal context/budget change; GREEN exact values, cleanup and small budget.
- [x] Prior-duration preflight then bounded selected tests, no local expensive constructor.
- [x] One independent whole-package review; all findings including Minors closed.
- [x] Same engine/input/runtime/state fences; isolated pinned raw A-B/B-A120s trials and separate work attribution.
- [x] Retain only measured complete-operation benefit; otherwise archive/restore.
- [ ] One bundled proof/full hosted gate if retained.

Restart unit one300s test file or120s independent trial;900s validation invocation,
310s next-file reserve and15minutes publication reserve. Existing compatible green
baseline reused. Ledger: membership-read-scope/progress.md; no shared task interfaces.
Standing authorization continues inline without routine approval pauses.
