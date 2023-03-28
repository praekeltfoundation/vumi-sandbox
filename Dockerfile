FROM ghcr.io/praekeltfoundation/vumi-base:no-wheelhouse AS builder

COPY . /build
WORKDIR /build

RUN pip install --upgrade pip
RUN pip wheel -w /wheels -r requirements.txt


FROM ghcr.io/praekeltfoundation/vumi-base:no-wheelhouse
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
