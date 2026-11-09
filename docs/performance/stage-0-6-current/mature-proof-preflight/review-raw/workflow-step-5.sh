set -euo pipefail
status=0
timeout --signal=TERM --kill-after=30s 35m python -m simulation.stage_0_6_proof_mature_preflight run --root "$GITHUB_WORKSPACE" --config simulation/stage_0_6_proof_mature_request.json 2>&1 | tee evidence/preflight.log || status=$?
python -m simulation.stage_0_6_proof_mature_preflight record-exit --root "$GITHUB_WORKSPACE" --status "$status"
exit "$status"

