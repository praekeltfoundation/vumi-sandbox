FROM praekeltfoundation/vumi
MAINTAINER Praekelt Foundation <dev@praekeltfoundation.org>

# Install nodejs 4.x LTS release
RUN apt-get-install.sh apt-transport-https curl && \
    curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key \
        | apt-key add - && \
    echo "deb https://deb.nodesource.com/node_4.x jessie main" \
        > /etc/apt/sources.list.d/nodesource.list && \
    apt-get-purge.sh curl
ENV NODEJS_VERSION "4.3.1"
RUN apt-get-install.sh nodejs=${NODEJS_VERSION}*

ENV VXSANDBOX_VERSION "0.6.0"
RUN pip install vxsandbox==$VXSANDBOX_VERSION

ENV WORKER_CLASS "vxsandbox.worker.StandaloneJsFileSandbox"
