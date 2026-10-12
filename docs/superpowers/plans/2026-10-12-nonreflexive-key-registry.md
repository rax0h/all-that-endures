# Native nonreflexive key identity: first implementation boundary

Continue the authorized inline Stage 0.5 closeout. This component does not
activate a format or claim that persisted NaN equality has been fixed.

The existing scalar entry codec collapses distinct NaN identities. Persisted
tokens will need stable identities for native NaN components, including values
held inside tuples, frozensets and Ref objects. Native floats cannot have weak
references. Add an explicit NaN-only binding operation to the existing
LazyIdentityRegistry, using its existing allocator and forward/reverse maps.
Ordinary mutable bindings remain weak. No second identity dictionary exists.

A callable conditional root owns one native float. CPython reference counts
distinguish an externally held float from one owned only by that root. A FIFO
queue checks at most 256 entries per collection call, without enumerating live
bindings or placements. Existing token checks protect cleanup against address
reuse. Close releases all roots. Diagnostics report strong roots and queue work.
This follows the existing actual-source memo lifetime mechanism; native
non-weak-referenceable key components require the same explicit accounting.

1. Write RED tests for distinct/reused identities, held nested components,
   checked rebinding, no-alias release, bounded collection and rejection.
2. Implement the narrow registry operation and collection queue.
3. Run focused registry tests and affected existing identity/recursive lifetime
   tests, record results and publish an exact-tree checkpoint.
4. Separately integrate closed NaN backing references with key projection,
   recursive decoding, physical owners, copy/restore and portable detach.
   Admission must hold actual D until publication; acknowledgement must release
   new input D directly, leaving only retained aliases and bounded deferred work.
5. Remove pending equality markers only after the 12 exposed RED cases and
   key-component sharing, fault and H-scaling tests pass against final integration.

Rank, gameplay, PR14 and prior P5 certification remain unchanged. Run the final
applicable suite and independent review only after the complete .5 source is stable.
