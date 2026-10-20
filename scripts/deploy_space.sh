#!/usr/bin/env bash
# Publish the app to the Hugging Face Space (free CPU basic hardware). Hugging Face builds the Docker image itself.
#   scripts/deploy_space.sh            # stage only, into backend/data/work/space_build
#   scripts/deploy_space.sh --push     # stage and upload (needs `hf auth login` with a write token once)
# GitHub Actions runs this on every push to main (.github/workflows/ci-cd.yml) with a short-lived token from
# Hugging Face Trusted Publishers, so no token is stored in GitHub.
set -euo pipefail
SPACE="${SPACE:-thebickersteth/voxpreference}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/backend/data/work/space_build"
HF="${HF:-$HOME/.venvs/voxpref/bin/hf}"
PYTHON="${PYTHON:-$HOME/.venvs/voxpref/bin/python}"

rm -rf "$OUT" && mkdir -p "$OUT"
rsync -a --exclude data --exclude __pycache__ --exclude .pytest_cache "$ROOT/backend/" "$OUT/backend/"
rsync -a --exclude node_modules --exclude dist "$ROOT/VoxPreference-frontend/" "$OUT/VoxPreference-frontend/"
cp "$ROOT/Dockerfile" "$ROOT/.dockerignore" "$OUT/"
cat > "$OUT/README.md" <<'EOF'
---
title: VoxPreference
emoji: 🗣️
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Preference Grammar analysis of Nigerian English speech
---

# VoxPreference

Automates Prof. C.U.C. Ugorji's Preference Grammar for Nigerian English: give target words, recordings
(single words, voice notes or whole podcasts) and a ranking of the six tenets; the app hears how each speaker
pronounced the sound, counts the variants, and returns the operability table and the preferred pronunciation.

Source and documentation: https://github.com/Oluwademiladeogo/VoxPreference (see backend/pg/README.md).
Runs on free CPU hardware: short clips take about a minute; a long podcast takes much longer.
EOF
echo "staged in $OUT ($(du -sh "$OUT" | cut -f1))"

if [[ "${1:-}" == "--push" ]]; then
  "$HF" auth whoami || true  # a CI token from Trusted Publishers has no user behind it
  # upload into the existing Space without `hf upload`, whose create-repo step is refused with 402 for Docker
  # Spaces on free accounts since mid-2026 (Spaces created before that keep their free CPU basic hardware);
  # delete_patterns removes files not in this upload (the Space's git history keeps them)
  "$PYTHON" - "$SPACE" "$OUT" <<'PY'
import sys
from huggingface_hub import HfApi
print(HfApi().upload_folder(repo_id=sys.argv[1], repo_type="space", folder_path=sys.argv[2], path_in_repo=".",
                            delete_patterns=["*"], commit_message="Update VoxPreference"))
PY
fi
