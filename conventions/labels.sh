#!/usr/bin/env bash
# Create the jh-loops label set in a target repo (design §6). Idempotent (--force).
# Usage: ./labels.sh <owner/repo>
set -euo pipefail
REPO="${1:?usage: labels.sh <owner/repo>}"

gh label create agent       --repo "$REPO" --color 1f6feb --description "Autonomous agent may work this issue (opt-in)" --force
gh label create in-progress --repo "$REPO" --color fbca04 --description "Claimed by the loop; in progress"             --force
gh label create in-review   --repo "$REPO" --color 0e8a16 --description "PR opened; awaiting human review/merge"       --force
gh label create needs-spec  --repo "$REPO" --color d93f0b --description "Missing/unparseable Depends-on or AC (sticky)" --force
gh label create needs-human --repo "$REPO" --color b60205 --description "Needs a human; incl. 3-round failure (sticky)" --force

echo "Labels created on $REPO"
