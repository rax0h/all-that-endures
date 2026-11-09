set -euo pipefail
mkdir -p evidence
python -m pytest -q .github/tests/test_stage_0_6_proof_mature_preflight.py .github/tests/test_stage_0_6_retained_archive.py .github/tests/test_stage_0_6_retained_producer.py .github/tests/test_stage_0_6_retained_transport.py .github/tests/test_stage_0_6_retained_launch.py -o junit_family=legacy --junitxml=evidence/harness.xml 2>&1 | tee evidence/harness.log

