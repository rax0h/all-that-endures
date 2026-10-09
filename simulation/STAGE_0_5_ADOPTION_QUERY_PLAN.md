# Adoption query connection

Preserve exact strict thresholds (.008, .01, .22, .35, .62), native map insertion order, and consumer snapshot timing. Explicit conversion creates independent scalar adoption cells and ordered threshold memberships. Ordinary queries merge persisted matches with current touched cells, without scanning dormant adoption history.

Independently checked versioned bucket counts and settlement markers detect omitted query rows and missing known bucket authority. Cell changes and count changes publish in the same frozen hybrid save plan; recovery validates both. Unmarked legacy snapshots retain eager behavior. Full logical iteration remains an explicit operation.

Validation: meaningful regression tests before implementation; threshold edges, deletion/reinsertion, snapshot timing, H=1,000/10,000 with eight selected cells, atomic failure recovery, old pins, corruption, native simulation parity, and P5. This checkpoint does not replace final integrated proof or the single combined Astra review.
