#!/usr/bin/env bash
# Offers to apt install any packages listed in apt_packages.txt that are not already installed.
set -euo pipefail

list="$(dirname "$0")/apt_packages.txt"
missing=()
while read -r pkg; do
    pkg="${pkg%%#*}"
    pkg="${pkg//[[:space:]]/}"
    [ -z "$pkg" ] && continue
    dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed" || missing+=("$pkg")
done < "$list"

[ ${#missing[@]} -eq 0 ] && exit 0

cmd="sudo apt install ${missing[*]}"
echo "Missing system packages: ${missing[*]}"
read -r -p "Run '$cmd' now? [y/N]: " answer || true
case "$answer" in
    y|Y|yes|YES) $cmd ;;
    *) echo "Skipped. Run '$cmd' yourself before building." ;;
esac
