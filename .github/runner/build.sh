#!/usr/bin/env bash
# Build the CI job image from the pins in versions.env.
#
# This is the only supported way in: the Dockerfile declares its ARGs without defaults, so a plain
# `docker build` fails naming this script. That is deliberate — it is what keeps versions.env the one place
# a toolchain version is written, rather than one of two places that drift.
#
# Usage: .github/runner/build.sh [tag]        (tag defaults to today, e.g. slipwai-ci:2026-09-04)
#
# The build context is the repository root, not this directory, because the image warms pip's wheel cache
# from the three committed requirements files. Only those and this directory are sent — see .dockerignore.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)

# shellcheck source=versions.env
set -a; . "$here/versions.env"; set +a

tag=${1:-slipwai-ci:$(date +%F)}

echo "building $tag from $here/versions.env"
docker build \
  --tag "$tag" \
  --file "$here/Dockerfile" \
  --build-arg "PYTHON_VERSION=$PYTHON_VERSION" \
  --build-arg "PYTHON_BUILD=$PYTHON_BUILD" \
  --build-arg "PYTHON_SHA256=$PYTHON_SHA256" \
  --build-arg "NODE_VERSION=$NODE_VERSION" \
  --build-arg "NODE_SHA256=$NODE_SHA256" \
  --build-arg "GO_VERSION=$GO_VERSION" \
  --build-arg "GO_SHA256=$GO_SHA256" \
  --build-arg "JAVA_VERSION=$JAVA_VERSION" \
  --build-arg "JAVA_RELEASE=$JAVA_RELEASE" \
  --build-arg "JAVA_ARCHIVE=$JAVA_ARCHIVE" \
  --build-arg "JAVA_SHA256=$JAVA_SHA256" \
  --build-arg "TOFU_VERSION=$TOFU_VERSION" \
  --build-arg "TOFU_SHA256=$TOFU_SHA256" \
  --build-arg "KO_VERSION=$KO_VERSION" \
  --build-arg "KO_SHA256=$KO_SHA256" \
  --build-arg "PACK_VERSION=$PACK_VERSION" \
  --build-arg "PACK_SHA256=$PACK_SHA256" \
  "$root"

echo
echo "built $tag — now prove it carries what the repository expects:"
echo "  docker run --rm -v \"$root:/repo\" -w /repo $tag .github/runner/check-toolchains.sh"
