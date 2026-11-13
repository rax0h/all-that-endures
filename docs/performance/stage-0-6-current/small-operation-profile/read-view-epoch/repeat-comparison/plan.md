# Recheck the reported small-world timings

Daniel correctly noted that recent absolute timings are longer than earlier
results. The earlier 5.312s save/5.990s warm and later 7.722s save/9.224s warm
baseline are the same Python executable, source-file hashes, input database and
expected fresh state. Their cause is not established. The latest paired
candidate's 8.152s save/7.271s warm is also slower than that earlier observation.
The previously reported 21.2% warm reduction compares only the adjacent
baseline/candidate pair; it does not establish that the absolute time improved
against every earlier run.

Use two additional A-B/B-A pairs in a single execution session on the exact
same authenticated year1 input and qualified runtime. A is green runtime41d21d8;
B is current candidate4654b019. Each starts from its own disposable copy; the
existing comparison driver checks input/source/runtime/import identity and saved
and continued state. A successful trial and its phase output are retained if a
later trial fails. Restart only an incomplete trial using the existing driver
and a fresh output path; cross-session retries must be labelled as such and not
silently combined into a same-session pair. The full runtime fingerprint is
verified once for the session; each trial checks its Python version, engine
source hashes and input identity. Libraries are not rehashed between trials.
Results expire on relevant code/runtime/input drift.

The trial is the failure unit. Existing phase ceilings are 60/180/120/180/120s;
a 120s wall cap applies to each complete trial, with up to5s group termination
grace and5s leader reaping; its log is retained. Stop the matrix after a trial
fails; do not launch an expensive
mature constructor or repeat a completed compatible trial. Record per-trial
CPU/affinity/cgroup context where available and reserve 15 minutes for any
publication. Do not infer a specific cause of variability or a mature-world
performance claim from these few observations. Hosted validation runs separately
and existing successful jobs must not be repeated merely for this comparison.
