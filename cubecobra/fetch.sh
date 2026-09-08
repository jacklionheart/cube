#!/usr/bin/env bash
# Refresh cube lists from Cube Cobra.
set -euo pipefail
cd "$(dirname "$0")"

# cubecobra shortId : local directory
cubes=(
  "sealed:gaelaria"
  "elemental:elemental"
  "fantasia:fantasia"
)

for pair in "${cubes[@]}"; do
  id="${pair%%:*}"
  dir="${pair##*:}"
  mkdir -p "$dir"
  curl -sf "https://cubecobra.com/cube/download/csv/$id" -o "$dir/cards.csv"
  echo "$dir: $(($(wc -l < "$dir/cards.csv") - 1)) cards"
done
