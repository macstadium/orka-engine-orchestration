# syntax=docker/dockerfile:1
# Builds Semaphore from source with MacStadium branding compiled into the binary.
# To upgrade: docker build --build-arg SEMAPHORE_VERSION=vX.Y.Z semaphore/

# Stage 1: build frontend + Go binary
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

# Patch Auth.vue: swap login card icon, update background, add MacStadium logo
RUN sed -i 's|src="favicon.png"|src="orka-icon.png"|g' web/src/views/Auth.vue

RUN python3 <<'EOF'
import re
content = open('web/src/views/Auth.vue').read()

content = content.replace(
    "background-image: url(\"../assets/background.svg\");",
    "",
)
content = content.replace(
    "background-color: #005057;",
    "background: linear-gradient(135deg, #1e1e37 0%, #323151 100%);",
)
content = content.replace("background: #80808024;", "")

ms_logo = (
    '\n    <img\n'
    '      src="/macstadium-logo.png"\n'
    '      alt="MacStadium"\n'
    '      :style="{\n'
    "        position:'absolute',bottom:'28px',left:'50%',\n"
    "        transform:'translateX(-50%)',width:'110px',\n"
    "        opacity:'0.45',zIndex:'1'\n"
    '      }"\n'
    '    />'
)
content = content.replace(
    '<v-dialog v-model="loginHelpDialog"',
    ms_logo + '\n    <v-dialog v-model="loginHelpDialog"',
)

content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
open('web/src/views/Auth.vue', 'w').write(content)
EOF

# Patch App.vue: add Orka logo to nav drawer
RUN python3 <<'EOF'
content = open('web/src/App.vue').read()
content = content.replace(
    '<v-menu bottom max-width="235"',
    '<v-img src="/orka-logo.png" max-width="160" contain class="mt-4 mb-2 mx-auto" />\n      '
    + '<v-menu bottom max-width="235"',
)
open('web/src/App.vue', 'w').write(content)
EOF

RUN --mount=type=cache,target=/go/pkg \
    task deps APP_BUILD_TYPE=

RUN --mount=type=cache,target=/go/pkg \
    --mount=type=cache,target=/root/.cache/go-build \
    task build GOOS=${TARGETOS} GOARCH=${TARGETARCH} APP_BUILD_TYPE=

# Stage 2: runtime image
FROM alpine:3.21

ARG ANSIBLE_VERSION=11.1.0
ENV ANSIBLE_VERSION=${ANSIBLE_VERSION}
ARG ANSIBLE_VENV_PATH=/opt/semaphore/apps/ansible/${ANSIBLE_VERSION}/venv

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

RUN apk add --no-cache -U python3-dev build-base openssl-dev libffi-dev cargo

COPY requirements.txt /tmp/requirements.txt

RUN mkdir -p ${ANSIBLE_VENV_PATH} && \
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

USER 1001
EXPOSE 3000

ENV VIRTUAL_ENV="${ANSIBLE_VENV_PATH}"
ENV PATH="${ANSIBLE_VENV_PATH}/bin:${PATH}"

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/usr/local/bin/server-wrapper"]
