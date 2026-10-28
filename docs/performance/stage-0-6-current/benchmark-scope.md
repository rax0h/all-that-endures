# What the sub-second results establish

The1k/10k/100k scaling matrices count retained history values in controlled fixtures, not simulation years. For example, review-cleanup/native-scaling/size-100000.json records24.612s construction,2.572s audited admission, and0.129s unprofiled selected first-access/edit/save. Construction and admission were separate timings, outside the sub-second operation. Other matrix rows exercise specific bounded append/truncate/backing transitions, not a complete simulated year.

These native tests explicitly use the proof-aware machinery. The October28 mature benchmark calls ordinary open_lazy_world_session without private proof admission. open_audited_proof_world_session explicitly supplies that authority; ordinary opening does not activate it. Some changes share runtime code, but a passing proof fast-path matrix does not establish that a full mature save takes the same path or remains within covered transitions.

A full year changes many kinds of records, identities, relationships and owners. The actual mature receipt reports53m40s save,1.652million payload reads and8.602GB payload bytes read. This is measured failure of the current end-to-end target. It does not identify which individual checks account for that time.

Remaining work is real-world proof integration and evidence-led removal of unnecessary work, with checked fallbacks, authenticated opening, canonical restoration and full continuation preserved. A bounded profile of the ordinary first-year path supplies attribution; it is neither a fast-path speedup claim nor a substitute for later complete-world validation.
