# A Linux container that behaves like a stock Mac where slipwai can tell the difference.
# Base: the zsh image from the user's Dockerfile (Ubuntu, zsh, Oh My Zsh through deluan/zsh-in-docker).
# On top, what a Mac ships that Ubuntu does not:
#   /bin/sh and bash  -> GNU bash 3.2.57   (macOS never moved past 3.2, for licensing)
#   make              -> GNU Make 3.81     (Apple's Command Line Tools; Homebrew's newer one is `gmake`)
#   python3           -> CPython 3.9       (Apple's Command Line Tools)
#   Homebrew          -> for a non-root user whose login shell is zsh, `brew shellenv` in ~/.zprofile
# slipwai is told it is on macOS (SLIPWAI_HOST_SYSTEM=macos) so it takes the Homebrew routes. What this cannot
# be is Darwin: BSD sed/tar/grep, /opt/homebrew, Apple's SIP paths.
# Stage 1: bash 3.2.57 and make 3.81 predate modern compilers; Ubuntu 20.04's GCC 9 still builds them, and the
# binaries run on the newer glibc below. make's bundled glob is taught the glibc interface version it refuses.
FROM ubuntu:20.04 AS oldtools
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y build-essential wget ca-certificates bison && rm -rf /var/lib/apt/lists/*
RUN cd /tmp && wget -q https://ftp.gnu.org/gnu/bash/bash-3.2.57.tar.gz && tar xf bash-3.2.57.tar.gz \
    && cd bash-3.2.57 && ./configure --prefix=/opt/bash32 --without-bash-malloc >/dev/null \
    && make -j4 >/dev/null && make install >/dev/null && /opt/bash32/bin/bash --version | head -1
RUN cd /tmp && wget -q https://ftp.gnu.org/gnu/make/make-3.81.tar.gz && tar xf make-3.81.tar.gz && cd make-3.81 \
    && sed -i 's/# if _GNU_GLOB_INTERFACE_VERSION == GLOB_INTERFACE_VERSION/# if _GNU_GLOB_INTERFACE_VERSION >= GLOB_INTERFACE_VERSION/' glob/glob.c \
    && ./configure --prefix=/opt/make381 >/dev/null && make -j4 >/dev/null && make install >/dev/null \
    && /opt/make381/bin/make --version | head -1

# Stage 2: the user's zsh image, with Apple's tools dropped in.
FROM ubuntu:latest
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y wget curl git zsh sudo build-essential procps file ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=oldtools /opt/bash32 /opt/bash32
COPY --from=oldtools /opt/make381 /opt/make381
RUN /opt/bash32/bin/bash --version | head -1 && /opt/make381/bin/make --version | head -1

# Apple's python3 3.9, from python-build-standalone through a throwaway uv.
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/tmp/uvboot sh >/dev/null 2>&1 \
    && /tmp/uvboot/uv python install 3.9 --install-dir /opt/pythons >/dev/null 2>&1 \
    && ln -sf "$(ls -d /opt/pythons/cpython-3.9*/bin/python3.9 | head -1)" /usr/bin/python3 \
    && rm -rf /tmp/uvboot /root/.local/share/uv && python3 --version

# The Mac user: zsh login shell, passwordless sudo (as an admin user's `sudo` is, once authenticated), Oh My Zsh.
RUN useradd -m -s /usr/bin/zsh mac && echo 'mac ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/mac
USER mac
WORKDIR /home/mac
RUN sh -c "$(wget -qO- https://github.com/deluan/zsh-in-docker/releases/download/v1.2.1/zsh-in-docker.sh)" -- -t robbyrussell >/dev/null 2>&1
# Homebrew, the way its installer leaves a Mac: the prefix, and `brew shellenv` in ~/.zprofile.
RUN NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" >/dev/null 2>&1 \
    && echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.zprofile \
    && /home/linuxbrew/.linuxbrew/bin/brew --version | head -1

# Now make the shells and make Apple's. Done last, after everything above that needed the modern ones.
USER root
RUN ln -sf /opt/bash32/bin/bash /usr/bin/bash && ln -sf /opt/bash32/bin/bash /usr/bin/sh \
    && rm -f /usr/bin/make && ln -sf /opt/make381/bin/make /usr/bin/make \
    && sh --version | head -1 && make --version | head -1
USER mac
ENV SLIPWAI_HOST_SYSTEM=macos
CMD ["zsh", "-l"]
