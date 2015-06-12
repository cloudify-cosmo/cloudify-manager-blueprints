FROM debian:jessie
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY PYTHONBASE_NOTICE.txt /root/PYTHONBASE_NOTICE.txt

RUN apt-get update && \
    apt-get install -y curl python python-dev && \
    curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | python && \
    pip install virtualenv && \
    apt-get purge -y python-dev curl && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /root/.cache /var/lib/apt/lists/* /tmp/* /var/log/apt/*