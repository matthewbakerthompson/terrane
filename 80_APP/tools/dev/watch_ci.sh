#!/usr/bin/env bash
# Wait for the validate and Pages runs on one commit and print their
# conclusions, one line each. Needs `gh` signed in. Run it as a background
# task after a push:  bash 80_APP/tools/dev/watch_ci.sh "$(git rev-parse HEAD)"
sha="$1"
if [ -z "$sha" ]; then echo "usage: watch_ci.sh <commit-sha>" >&2; exit 2; fi
cd "$(git rev-parse --show-toplevel)" || exit 1
for i in $(seq 1 90); do
  out=$(gh run list --commit "$sha" --limit 6 --json name,status,conclusion,url,headSha \
    --template '{{range .}}{{.name}}	{{.status}}	{{.conclusion}}	{{slice .headSha 0 7}}	{{.url}}{{"\n"}}{{end}}' 2>&1)
  n=$(printf "%s" "$out" | grep -c "completed")
  total=$(printf "%s" "$out" | grep -c "	")
  if [ "$total" -ge 2 ] && [ "$n" -ge 2 ]; then
    printf "%s\n" "$out"
    exit 0
  fi
  sleep 20
done
printf "timed out\n%s\n" "$out"
exit 1
