#!/bin/bash
set -euo pipefail

curl -sL https://api.github.com/repos/near/nearcore/releases/latest | jq -r ".tag_name" > near-nearcore-latest.txt
