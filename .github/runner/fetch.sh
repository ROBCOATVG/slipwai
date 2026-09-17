#!/usr/bin/env bash
# Download one archive and refuse to hand it on unless it is byte-for-byte the one we pinned.
#
# Every toolchain in the image comes through here, so "pinned" means the digest in versions.env and not just
# a version number in a URL: a release re-cut under the same tag, a compromised mirror or a truncated
# download all fail the build here, with the URL and both digests named, rather than becoming an image the
# runners quietly serve to every job.
set -euo pipefail

url=$1
expected=$2
destination=$3

curl --fail --show-error --silent --location --retry 3 --retry-delay 2 --output "$destination" "$url"

actual=$(sha256sum "$destination" | cut -d' ' -f1)
if [ "$actual" != "$expected" ]; then
  echo "checksum mismatch for $url" >&2
  echo "  expected $expected" >&2
  echo "  actual   $actual" >&2
  rm -f "$destination"
  exit 1
fi
