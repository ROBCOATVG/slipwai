# The image every `runs-on: ubuntu-latest` job runs in.
#
# Why it exists: the job container is discarded when the job ends, so anything a job installs is installed
# again by the next one. Seven `actions/setup-*` steps per job, ten jobs a run, meant seven toolchains
# downloaded ten times — about a minute of every job — and the setup actions ask api.github.com which
# version to fetch, unauthenticated, which exhausted this host's 60-requests-an-hour limit and left the
# steps falling back to direct downloads. Baking the toolchains in makes all of that a no-op: the tools are
# in the image, and `.github/actions/toolchains` only checks that they are the versions the repository
# expects (`check-toolchains.sh`).
#
# The base stays ghcr.io/catthehacker/ubuntu:act-latest — act_runner relies on its layout, and it already
# carries the docker CLI (jobs reach the host daemon through the socket act_runner mounts), git, make, curl
# and binutils (which is what PyInstaller needs objdump/objcopy for, so no job has to apt-get it).
#
# Build it with `.github/runner/build.sh`, which is what supplies every ARG below from
# `.github/runner/versions.env`. Nothing here has a default on purpose: a version that reaches this image
# without going through that file is exactly the drift this design exists to prevent.
FROM ghcr.io/catthehacker/ubuntu:act-latest

ARG PYTHON_VERSION
ARG PYTHON_BUILD
ARG PYTHON_SHA256
ARG NODE_VERSION
ARG NODE_SHA256
ARG GO_VERSION
ARG GO_SHA256
ARG JAVA_VERSION
ARG JAVA_RELEASE
ARG JAVA_ARCHIVE
ARG JAVA_SHA256
ARG TOFU_VERSION
ARG TOFU_SHA256
ARG KO_VERSION
ARG KO_SHA256
ARG PACK_VERSION
ARG PACK_SHA256

SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-c"]

# An unset ARG is an empty string rather than an error, and an empty version would silently build an image
# that downloads whatever "" resolves to. Fail here instead, naming the way in.
RUN for name in PYTHON_VERSION PYTHON_BUILD PYTHON_SHA256 NODE_VERSION NODE_SHA256 GO_VERSION GO_SHA256 \
                JAVA_VERSION JAVA_RELEASE JAVA_ARCHIVE JAVA_SHA256 TOFU_VERSION TOFU_SHA256 \
                KO_VERSION KO_SHA256 PACK_VERSION PACK_SHA256; do \
      if [ -z "${!name:-}" ]; then \
        echo "build-arg $name is empty — build with .github/runner/build.sh, which reads versions.env" >&2; \
        exit 1; \
      fi; \
    done

RUN apt-get update \
 && apt-get install --yes --no-install-recommends unzip xz-utils ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Every archive is fetched, checked against the digest its publisher lists, and only then unpacked — so a
# substituted tarball fails this build rather than the runners.
COPY .github/runner/fetch.sh /usr/local/libexec/fetch.sh

# CPython, relocatable and carrying its own pip and venv. Deliberately NOT Ubuntu's python3: that is 3.12,
# and apt's own tooling imports it, so replacing it breaks the package manager. This goes earlier on PATH
# instead, which leaves /usr/bin/python3 for the system and gives every job `python3` == 3.13.
# `scripts/verify` and `scripts/build-wheel` both run `python3 -m pip install --target`, so pip has to be
# importable from this interpreter — the install_only build ships it.
RUN /usr/local/libexec/fetch.sh \
      "https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_BUILD}/cpython-${PYTHON_VERSION}%2B${PYTHON_BUILD}-x86_64-unknown-linux-gnu-install_only.tar.gz" \
      "${PYTHON_SHA256}" /tmp/python.tar.gz \
 && mkdir -p /opt/python \
 && tar -xzf /tmp/python.tar.gz -C /opt/python --strip-components=1 \
 && rm /tmp/python.tar.gz \
 && /opt/python/bin/python3 -m ensurepip --upgrade >/dev/null 2>&1 || true

# The base image bundles a node of its own and puts it first on PATH. This one is installed to /opt/node and
# PATH is rewritten below so that this is the one a job gets; `check-toolchains.sh` is what fails the build
# if that ever stops being true.
RUN /usr/local/libexec/fetch.sh \
      "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
      "${NODE_SHA256}" /tmp/node.tar.xz \
 && mkdir -p /opt/node \
 && tar -xJf /tmp/node.tar.xz -C /opt/node --strip-components=1 \
 && rm /tmp/node.tar.xz

RUN /usr/local/libexec/fetch.sh \
      "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" \
      "${GO_SHA256}" /tmp/go.tar.gz \
 && tar -xzf /tmp/go.tar.gz -C /usr/local \
 && rm /tmp/go.tar.gz

# A JDK is all this is for: a generated Java project drives its build through the `./mvnw` it commits, which
# fetches the Maven its `maven-wrapper.properties` pins.
RUN /usr/local/libexec/fetch.sh \
      "https://github.com/adoptium/temurin25-binaries/releases/download/${JAVA_RELEASE//+/%2B}/OpenJDK25U-jdk_x64_linux_hotspot_${JAVA_ARCHIVE}.tar.gz" \
      "${JAVA_SHA256}" /tmp/java.tar.gz \
 && mkdir -p /opt/java \
 && tar -xzf /tmp/java.tar.gz -C /opt/java --strip-components=1 \
 && rm /tmp/java.tar.gz

# The production target's tools: `tofu validate` over every generated stack, and ko and pack for the images
# `test_images` and `test_launcher` build and start.
RUN /usr/local/libexec/fetch.sh \
      "https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_linux_amd64.zip" \
      "${TOFU_SHA256}" /tmp/tofu.zip \
 && unzip -q -o /tmp/tofu.zip tofu -d /usr/local/bin \
 && chmod +x /usr/local/bin/tofu \
 && rm /tmp/tofu.zip

RUN /usr/local/libexec/fetch.sh \
      "https://github.com/ko-build/ko/releases/download/v${KO_VERSION}/ko_${KO_VERSION}_Linux_x86_64.tar.gz" \
      "${KO_SHA256}" /tmp/ko.tar.gz \
 && tar -xzf /tmp/ko.tar.gz -C /usr/local/bin ko \
 && chmod +x /usr/local/bin/ko \
 && rm /tmp/ko.tar.gz

RUN /usr/local/libexec/fetch.sh \
      "https://github.com/buildpacks/pack/releases/download/v${PACK_VERSION}/pack-v${PACK_VERSION}-linux.tgz" \
      "${PACK_SHA256}" /tmp/pack.tgz \
 && tar -xzf /tmp/pack.tgz -C /usr/local/bin pack \
 && chmod +x /usr/local/bin/pack \
 && rm /tmp/pack.tgz

# act runs each step with a non-login, non-interactive `bash -e`, so /etc/profile.d is never sourced and the
# container's own environment is the only thing a step inherits. Everything a job needs on PATH therefore
# has to be set here — and ahead of the base image's own entries, which is what makes the node above win
# over the one the base image bundles.
ENV JAVA_HOME=/opt/java
ENV PATH=/opt/python/bin:/opt/node/bin:/usr/local/go/bin:/opt/java/bin:${PATH}

# `scripts/verify` installs the pinned ruff and mypy into an ignored `.python-tools` on first use, and the
# executable and wheel builds do the same with their own requirements — into the checkout, which is fresh
# every job, so the install itself cannot be cached. Warming pip's wheel cache in the image is the next best
# thing: the wheels are already local, so the install is a copy rather than a download. Going stale is
# harmless and self-correcting — pip fetches what the cache lacks — so this is never a correctness question,
# only a speed one.
ENV PIP_CACHE_DIR=/opt/pip-cache
COPY requirements-dev.txt requirements-build.txt requirements-publish.txt /tmp/requirements/
RUN python3 -m pip download --disable-pip-version-check --quiet --dest /tmp/wheels \
      -r /tmp/requirements/requirements-dev.txt \
      -r /tmp/requirements/requirements-build.txt \
      -r /tmp/requirements/requirements-publish.txt \
 && rm -rf /tmp/wheels /tmp/requirements

# Proof the image is what it claims before it is ever tagged. This is the same set `check-toolchains.sh`
# asserts from the checkout at job time; here it only has to run, so a broken PATH or a missing shared
# library fails the build instead of the first CI run.
RUN python3 --version && node --version && npm --version && go version \
 && java -version && tofu version && ko version && pack --version \
 && docker --version && git --version && make --version | head -1
