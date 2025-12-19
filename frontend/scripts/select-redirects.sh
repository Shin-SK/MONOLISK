#!/usr/bin/env bash
set -euo pipefail

# 必須: REDIRECTS_PROFILE=prod|stg|sandbox
case "${REDIRECTS_PROFILE:-}" in
  prod|stg|sandbox) ;;
  *)
    echo "ERROR: REDIRECTS_PROFILE must be 'prod' or 'stg' or 'sandbox' (current: '${REDIRECTS_PROFILE:-<unset>}')" >&2
    exit 1
    ;;
esac

SRC="public/_redirects.${REDIRECTS_PROFILE}"
DST="public/_redirects"
[ -f "$SRC" ] || { echo "ERROR: missing $SRC" >&2; exit 1; }
cp -f "$SRC" "$DST"
echo "[redirects] use $SRC -> $DST"