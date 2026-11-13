# Countersign in this repo

This is a demo copy of [junction26-messagepack-csharp](https://github.com/te-industry-tech-office/junction26-messagepack-csharp)
(base `32258fdb`) with Countersign wired into its pull-request flow. The four agent-written branches are open as PRs.

- `snapshot/`: Countersign pinned at the commit in `snapshot/PINNED` (pipeline code, the signed mandate, owners'
  public keys, requirement sets, and the recorded facts and reviews for changes 2283, 2234, 2129, 2297). Vendored
  because Zawaer/countersign is private; `vendor.sh` refreshes it.
- `config.yaml`: GitHub login per mandate owner, the ledger branch and the status name.
- `.github/workflows/countersign.yml`: on every PR push, builds the evidence pack, posts it as a sticky comment,
  sets the `countersign/tier` status and routes the PR to the owner.
- `.github/workflows/countersign-command.yml`: handles `/countersign accept|reject|request-changes|status` comments.
- Branch `countersign-ledger`: the append-only ledger. CI appends an entry only after verifying the owner's
  Ed25519 signature; `python -m countersign verify-ledger` re-checks it.

The owner countersigns from their own machine (CI never holds the key):

```bash
git clone https://github.com/Zawaer/countersign-messagepack-demo && cd countersign-messagepack-demo
PYTHONPATH=.countersign/snapshot <python with pyyaml + cryptography> -m countersign.github sign-pr <PR number> \
  --gh-repo Zawaer/countersign-messagepack-demo --as Toivo --decision accept --note "..." \
  --key <path to toivo.key> --post
```

The flow, what is real and what is recorded: see `docs/PR_FLOW.md` in Zawaer/countersign.
