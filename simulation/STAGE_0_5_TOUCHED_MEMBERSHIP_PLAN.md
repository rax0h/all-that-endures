# Bound touched-membership overlays by current dirty state

Defect: `_LazyInstitutionRecordTable._index_touched_memberships` only adds candidates, retaining every past status/query bucket for a dirty record until save. Current D=1 can therefore retain1k/10k obsolete metadata buckets after repeated edits.

Design: retain current membership markers per touched key. On change, subtract its old-only memberships, prune empty buckets, add current-only memberships, and replace that key's marker set. Delete removes that key from both overlays; successful save clears both. Never inspect cold rows or other touched owners. Preserve the existing persistent checked baseline and exact query results, failure/retry and owner identity.

Tests: at1k/10k unsaved status changes to one notice, retained candidate markers equal current membership width; old status query excludes it, current query includes it. Save/reopen retains the final status and clears overlay sidecars; deletion clears only its markers. Run existing lazy institution and transmission consumers plus relevant ownership/currency/people gates.
