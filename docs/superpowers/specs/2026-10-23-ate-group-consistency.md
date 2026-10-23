# Root-bound group consistency

Recovered contract after temporary workspace cleanup on October 23. The last published baseline is c4cfe473db93090ddabf25762fc26740846a6149. Unpublished local commits and raw verification output were not recovered. Reconstructed code must earn fresh evidence; historical test counts are not evidence for this tree.

Implement an inactive raw group reader joining externally accepted retained version, group occurrence, per-owner occurrence, and link query roots to the existing identity catalog. Reuse the catalog's owner radix, group count/digests, canonical encoded absolute-path links, allocator and retirement range semantics. No alternate publisher or canonical registry. Readers share one checked snapshot, reject caller codec hooks, bound metadata before decoding, and never fetch owner/archive payload bodies.

The query source must select positions from an immutable ordered root, then check each selected physical interval and checksum. Both nonempty and empty retained scopes must stay bounded as newer rows grow. Root selection does not certify unselected physical inventory.

Return the complete requested raw group or raise an explicit budget error. Defaults: 4096 members, 2 MiB aggregate decoded source/raw fields, 1 MiB per source and operational metadata. Root commitments, exact store/codec/generation/pin context and allocator agreement are mandatory. Validate selected owner source interval metadata without reading its payload. Old ordinary overwritten payload availability remains gated.

No World admission, target existence/kind checks, complete topology/namespace inventory, manifests, retention/collection, writer fencing or publication protocol is enabled. Existing World paths stay unchanged. Component diagnostics are not World performance acceptance.
