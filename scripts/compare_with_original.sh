#!/bin/sh
# Runs the same command session against the original starter commit and the current
# working tree, then diffs the outputs. Usage: sh scripts/compare_with_original.sh
set -u
ORIGINAL=${ORIGINAL:-82ed75e}
TMP=$(mktemp -d)
git worktree add -q "$TMP/original" "$ORIGINAL"
session() {
  data="$2/state.json"
  for args in \
    "catalog" \
    "quote --item notebook:2" \
    "quote --customer student --fulfillment delivery --item hoodie:2" \
    "quote --fulfillment delivery --item hoodie:3" \
    "quote --customer student --item bag:2" \
    "place --item mug:1 --item notebook:2" \
    "place --customer student --fulfillment delivery --item hoodie:2" \
    "place --item laptop:1" \
    "place --item mug:0" \
    "orders" \
    "show ORD-0002" \
    "cancel ORD-0001" \
    "show ORD-0099" \
    "catalog"; do
    echo "\$ $args"
    (cd "$1" && python3 -m supplydesk --data "$data" $args 2>&1; echo "exit=$?")
  done
}
mkdir -p "$TMP/a" "$TMP/b"
session "$TMP/original" "$TMP/a" > "$TMP/original.txt"
session "$(pwd)" "$TMP/b" > "$TMP/current.txt"
if diff -u "$TMP/original.txt" "$TMP/current.txt"; then
  echo "SAME OUTPUT: $(grep -c '^\$' "$TMP/current.txt") commands produced identical output and exit codes"
fi
git worktree remove --force "$TMP/original"; rm -rf "$TMP"
