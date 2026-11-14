#!/bin/sh
# Re-vendor the pinned Countersign snapshot: the pipeline code plus the recorded inputs for the four changes
# and for demo-docs1, the agent-written README fix on branch ju26-demo-docs1.
# usage: .countersign/vendor.sh <path to a Zawaer/countersign clone> <commit>
set -eu
src=$1; commit=$2
here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$here/snapshot" && mkdir -p "$here/snapshot"
git -C "$src" archive "$commit" pyproject.toml countersign mandate requirements keys prompts ledger \
  evidence/2283 evidence/2234 evidence/2129 evidence/2297 evidence/demo-docs1/facts.json \
  reviews/2283 reviews/2234 reviews/2129 reviews/2297 reviews/demo-docs1 | tar -x -C "$here/snapshot"
git -C "$src" rev-parse "$commit" > "$here/snapshot/PINNED"
echo "vendored Zawaer/countersign@$(cat "$here/snapshot/PINNED")"
