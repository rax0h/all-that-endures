# Proof timeout retry

Run40450442032 passed all4301 full-suite and1205 proof tests. Its proof job
hit the40-minute job deadline during the last identity-group100k matrix;
27 other matrices completed. Artifact archive hashes, source/runtime and XML
counts were verified. This is partial acceptance, not a green proof job.

Increase proof budget to60 minutes. An exact commit-message exception skips
the already-passed full suite for this retry only. Before tests, the proof job
fetches the accepted commit and requires every repository path except docs and
this workflow to be byte-identical. Source changes fail the retry. Ordinary
candidates continue running both jobs. No runtime, test or benchmark changes.

Remove this one-candidate exception with the next runtime candidate. Do not
poll this hosted job; wait for the user’s green.
