FROM debian:jessie
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY NGINX_NOTICE.txt /root/NGINX_NOTICE.txt

ENV DOCKER_ENV=True

RUN echo "deb http://nginx.org/packages/ubuntu/ trusty nginx" >> /etc/apt/sources.list.d/nginx.list && \
    apt-key adv --fetch-keys http://nginx.org/keys/nginx_signing.key && \
    apt-get update && \
    apt-get install -y --no-install-recommends nginx && \
    mkdir -p /var/log/cloudify/nginx && \
    rm -rf /var/lib/apt/lists && \
    apt-get autoremove -y

COPY config/default /etc/nginx/sites-available/default

EXPOSE 80 53229

CMD nginx -c /etc/nginx/nginx.conf -g "daemon off;"