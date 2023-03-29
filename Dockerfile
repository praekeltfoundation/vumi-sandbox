FROM ghcr.io/praekeltfoundation/pypy-base-nw:2-buster AS builder

RUN apt-get update
RUN apt-get -yy install build-essential libssl-dev libffi-dev

COPY . ./

RUN pip install --upgrade pip
# We need the backport of the typing module to build Twisted.
RUN pip install typing==3.10.0.0

RUN pip wheel -w /wheels -r /requirements.txt


# TODO: Switch to a versioned vumi image once we have one.
FROM ghcr.io/praekeltfoundation/vumi-base:sha-b99680b
MAINTAINER Praekelt Foundation <dev@praekeltfoundation.org>

# We need both of these outside the build, so we may as well pass them both in
# and save some work extracting the major version.
ARG NODEJS_MAJOR="18"
ARG NODEJS_VERSION="18.15.0"

# Install nodejs from upstream apt repo
RUN apt-get-install.sh apt-transport-https curl gnupg2 && \
    curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key \
        | apt-key add - && \
    echo "deb https://deb.nodesource.com/node_${NODEJS_MAJOR}.x buster main" \
        > /etc/apt/sources.list.d/nodesource.list && \
    apt-get-purge.sh curl gnupg2

RUN apt-get-install.sh nodejs=${NODEJS_VERSION}*

COPY --from=builder /wheels /wheels
RUN pip install -f /wheels vxsandbox

ENV WORKER_CLASS "vxsandbox.worker.StandaloneJsFileSandbox"
