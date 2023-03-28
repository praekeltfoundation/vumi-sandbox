FROM ghcr.io/praekeltfoundation/pypy-base-nw:2-buster AS builder

RUN apt-get update
RUN apt-get -yy install build-essential libssl-dev libffi-dev

COPY . ./

RUN pip install --upgrade pip
# We need the backport of the typing module to build Twisted.
RUN pip install typing==3.10.0.0

RUN pip wheel -w /wheels -r /requirements.txt


FROM ghcr.io/praekeltfoundation/pypy-base-nw:2-buster
MAINTAINER Praekelt Foundation <dev@praekeltfoundation.org>

# Install nodejs 12.x LTS release
RUN apt-get-install.sh apt-transport-https curl gnupg2 && \
    curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key \
        | apt-key add - && \
    echo "deb https://deb.nodesource.com/node_12.x buster main" \
        > /etc/apt/sources.list.d/nodesource.list && \
    apt-get-purge.sh curl gnupg2

ENV NODEJS_VERSION "12.22.12"
RUN apt-get-install.sh nodejs=${NODEJS_VERSION}*

COPY --from=builder /wheels /wheels
RUN pip install -f /wheels -r /requirements.txt

ENV WORKER_CLASS "vxsandbox.worker.StandaloneJsFileSandbox"
