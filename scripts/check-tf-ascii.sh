#!/usr/bin/env bash
# Fails if any Terraform file contains non-ASCII characters.
# AWS rejects em/en dashes and other non-ASCII in resource descriptions,
# group names, tag values, etc. Use plain ASCII (e.g. '-' instead of '—').
set -euo pipefail

bad=0
for f in "$@"; do
  if perl -ne 'if (/([^\x00-\x7F])/) { print "$ARGV:$.: $_"; exit 1 }' "$f"; then
    :
  else
    bad=1
  fi
done

if [ "$bad" -ne 0 ]; then
  echo "" >&2
  echo "Non-ASCII characters found in Terraform files." >&2
  echo "AWS rejects these in resource descriptions/names. Use plain ASCII (e.g. '-' instead of '—')." >&2
  exit 1
fi
