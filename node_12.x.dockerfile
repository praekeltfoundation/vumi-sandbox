FROM praekeltfoundation/vumi:0.6.18-pypy
MAINTAINER Praekelt Foundation <dev@praekeltfoundation.org>

# Install nodejs 12.x LTS release
RUN apt-get-install.sh apt-transport-https curl gnupg2 && \
    curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key \
        | apt-key add - && \
    echo "deb https://deb.nodesource.com/node_12.x jessie main" \
        > /etc/apt/sources.list.d/nodesource.list && \
    apt-get-purge.sh curl gnupg2

ENV NODEJS_VERSION "12.16.3"
RUN apt-get-install.sh nodejs=${NODEJS_VERSION}*



ENV VXSANDBOX_VERSION "0.6.2a3"
RUN apt-get-install.sh gcc && \
    pip install vxsandbox==$VXSANDBOX_VERSION && \
    apt-get-purge.sh gcc

ENV WORKER_CLASS "vxsandbox.worker.StandaloneJsFileSandbox"
