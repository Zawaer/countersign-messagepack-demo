# Countersign ledger

`ledger.jsonl` is the append-only, hash-chained ledger for this repo. Each line is an entry
`{seq, ts, type, payload, prev, signer, hash, sig}`: `hash` covers the entry, `prev` is the previous entry's hash,
and `sig` is the signer's Ed25519 signature over `hash`, checked against `.countersign/snapshot/keys/<signer>.pub`
on `main`.

The first entries are copied from Zawaer/countersign at the pinned commit (the owner signing the mandate). Signoff
entries are appended by the `Countersign command` workflow, only after it verified the owner's signature, the pack
hash and the chain. CI never signs: it has no private key. Re-check everything from a clone of `main`:

    git show origin/countersign-ledger:ledger.jsonl > .countersign/snapshot/ledger/ledger.jsonl
    PYTHONPATH=.countersign/snapshot python3 -m countersign verify-ledger --root .countersign/snapshot
