FROM debian:jessie
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY INFLUXDB_NOTICE.txt /root/INFLUXDB_NOTICE.txt
COPY scripts/* /opt/scripts/

ENV INFLUXDB_VERSION=0.8.8 \
    DOCKER_ENV=True \
    INFLUXDB_HOME=/opt/influxdb

RUN apt-get update && \
    apt-get install -y curl && \
    curl http://s3.amazonaws.com/influxdb/influxdb_${INFLUXDB_VERSION}_amd64.deb --create-dirs -o /tmp/influxdb.deb && \
    dpkg -i /tmp/influxdb.deb && \
    # starting influxdb as daemon to create cloudify db
    /usr/bin/influxdb-daemon -config=${INFLUXDB_HOME}/shared/config.toml && \
    chmod +x /opt/scripts/wait_for_port && sleep 3 && /opt/scripts/wait_for_port 8086 && \
    curl -s "http://localhost:8086/db?u=root&p=root" -d "{\"name\": \"cloudify\"}" && \
    mkdir -p /var/log/cloudify/influxdb && \
    rm -rf /var/lib/apt/lists && \
    rm -rf /tmp/* && \
    apt-get purge curl -y && \
    apt-get autoremove -y

COPY config/config.toml ${INFLUXDB_HOME}/shared/config.toml

VOLUME ${INFLUXDB_HOME}/shared/data

EXPOSE 8086 8083

CMD /usr/bin/influxdb -config=${INFLUXDB_HOME}/shared/config.toml