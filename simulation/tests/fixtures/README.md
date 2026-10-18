# Retained audit receipt fixture

`continuation-audit1001.zip` is the exact downloaded public GitHub artifact
12148235361 from successful run39152488567, job117748798734. It contains only
the actual audit.json metadata, not a World database. Archive35605 bytes,
SHA256 `c9b502c71e355644b26ae4b0bdb3ca3edc6dfb567335d73465da009af4cd1943`.
Member223650 bytes, SHA256
`4be22bcfeea6dd71e588d8f65c4e63ab7538c2faca7c4a07640b26b2f1252b97`.

It reproduces the integer-year JSON ordering defect and proves exact existing
audit reuse through the real receipt reader and acceptance validator. Synthetic
digest metadata used by those unit tests only exercises composition; it does
not certify an actual mature digest or Stage0.5 acceptance. Fresh CI separately
authenticates and downloads this same artifact from its original producer.
