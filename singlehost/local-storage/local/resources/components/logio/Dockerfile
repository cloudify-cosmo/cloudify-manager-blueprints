FROM cloudify_javabase:latest

RUN apt-get update && \
    apt-get install -y curl make g++ && \
    curl -sL https://deb.nodesource.com/setup | bash - && \
    apt-get install -y nodejs && \
    npm install -g log.io --user "root" && \
    mkdir /var/log/cloudify

COPY harvester.conf /root/.log.io/harvester.conf

EXPOSE 28778

CMD log.io-server & log.io-harvester