#!/usr/bin/env bash
set -euo pipefail

# Create the standalone repository locally and attach its canonical remote.
# The remote must be empty before the first push.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -e "$root/.git" ]]; then
  echo "quant/ is already a Git repository" >&2
  exit 1
fi
cd "$root"
git init --initial-branch=main
git add .
git commit -m "Initialize QuantLab AI research platform"
git remote add origin git@github.com:CastaliaInstitute/quant.git
cat <<'MSG'
Local repository initialized. After creating an empty public GitHub repository at
CastaliaInstitute/quant, publish the starter with:

  git push -u origin main

Then select GitHub Actions as the Pages build source. DNS should point the
quant.castalia.institute CNAME to castaliainstitute.github.io.
MSG
