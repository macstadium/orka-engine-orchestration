# syntax=docker/dockerfile:1
# Builds Semaphore from source with MacStadium branding compiled into the binary.
# This image is pushed to ghcr.io/macstadium/orka-engine-orchestration and used
# as the base image in semaphore/Dockerfile.
#
# To upgrade Semaphore: rebuild with --build-arg SEMAPHORE_VERSION=vX.Y.Z

# ---------------------------------------------------------------------------
# Stage 1: build frontend + Go binary
# ---------------------------------------------------------------------------
FROM --platform=$BUILDPLATFORM golang:1.24-alpine3.21 AS builder

ARG SEMAPHORE_VERSION=v2.17.36
ARG TARGETOS
ARG TARGETARCH

RUN apk add --no-cache -U \
    libc-dev curl nodejs npm git gcc zip unzip tar python3

WORKDIR /usr/local
RUN curl -sL https://taskfile.dev/install.sh | sh

WORKDIR /go/src/semaphore
RUN git clone --depth 1 --branch ${SEMAPHORE_VERSION} \
    https://github.com/semaphoreui/semaphore.git .

# Apply MacStadium theme
COPY overrides/vuetify.js web/src/plugins/vuetify.js

RUN sed -i "s/'#005057'/'#323151'/g" web/src/App.vue && \
    sed -i "s/'#003236'/'#1e1e37'/g" web/src/App.vue

RUN grep -rl "Enter to your account" web/src/ | \
    xargs sed -i 's/Enter to your account/Orka for VDI/g'

# Copy brand assets into the public folder
COPY assets/orka-icon.png          web/public/orka-icon.png
COPY assets/orka-logo.png          web/public/orka-logo.png
COPY assets/macstadium-logo.png    web/public/macstadium-logo.png
COPY assets/macstadium-favicon.png web/public/favicon.png

# Patch login page: swap icon, update background, add MacStadium logo
RUN sed -i 's|src="favicon.png"|src="orka-icon.png"|g' web/src/views/Auth.vue

COPY precompiled/patch_auth_vue.py /tmp/patch_auth_vue.py
RUN python3 /tmp/patch_auth_vue.py web/src/views/Auth.vue

# Patch nav drawer: add Orka logo
COPY precompiled/patch_app_vue.py /tmp/patch_app_vue.py
RUN python3 /tmp/patch_app_vue.py web/src/App.vue

RUN --mount=type=cache,target=/go/pkg \
    task deps APP_BUILD_TYPE=

RUN --mount=type=cache,target=/go/pkg \
    --mount=type=cache,target=/root/.cache/go-build \
    task build GOOS=${TARGETOS} GOARCH=${TARGETARCH} APP_BUILD_TYPE=

# ---------------------------------------------------------------------------
# Stage 2: runtime image
# ---------------------------------------------------------------------------
FROM alpine:3.21

RUN apk add --no-cache -U \
        bash curl git gnupg mysql-client openssh-client-default python3 py3-pip \
        rsync sshpass tar tini tzdata unzip wget zip jq && \
    rm -rf /var/cache/apk/* && \
    adduser -D -u 1001 -G root semaphore && \
    mkdir -p /tmp/semaphore /etc/semaphore /var/lib/semaphore /opt/semaphore && \
    chown -R semaphore:0 /tmp/semaphore /etc/semaphore /var/lib/semaphore /opt/semaphore && \
    find /usr/lib/python* -iname __pycache__ | xargs rm -rf

RUN printf 'Host *\n  StrictHostKeyChecking no\n  UserKnownHostsFile /dev/null\n' \
    > /etc/ssh/ssh_config.d/semaphore.conf

COPY --from=builder /go/src/semaphore/bin/semaphore /usr/local/bin/semaphore
COPY --from=builder \
    /go/src/semaphore/deployment/docker/server/server-wrapper \
    /usr/local/bin/server-wrapper

RUN chown semaphore:0 /usr/local/bin/semaphore /usr/local/bin/server-wrapper && \
    chmod +x /usr/local/bin/semaphore /usr/local/bin/server-wrapper

WORKDIR /home/semaphore

ARG ANSIBLE_VERSION=13.4.0
ARG ANSIBLE_VENV_PATH=/opt/semaphore/apps/ansible/${ANSIBLE_VERSION}/venv

COPY requirements.txt /tmp/requirements.txt

RUN apk add --no-cache -U python3-dev build-base openssl-dev libffi-dev cargo && \
    mkdir -p ${ANSIBLE_VENV_PATH} && \
    python3 -m venv ${ANSIBLE_VENV_PATH} --system-site-packages && \
    ${ANSIBLE_VENV_PATH}/bin/pip3 install --upgrade pip && \
    ${ANSIBLE_VENV_PATH}/bin/pip3 install --no-cache-dir \
        boto3 botocore requests pywinrm passlib && \
    ${ANSIBLE_VENV_PATH}/bin/pip3 install --no-cache-dir -r /tmp/requirements.txt && \
    apk del python3-dev build-base openssl-dev libffi-dev cargo && \
    rm -rf /var/cache/apk/* /tmp/requirements.txt && \
    find ${ANSIBLE_VENV_PATH} -iname __pycache__ | xargs rm -rf && \
    chown -R semaphore:0 /opt/semaphore

RUN mkdir -p /home/semaphore/.cache/ansible_facts && \
    chown -R semaphore:0 /home/semaphore/.cache

ENV VIRTUAL_ENV="${ANSIBLE_VENV_PATH}"
ENV PATH="${ANSIBLE_VENV_PATH}/bin:${PATH}"

USER 1001
EXPOSE 3000

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/usr/local/bin/server-wrapper"]
