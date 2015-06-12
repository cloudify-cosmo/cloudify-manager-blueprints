This directory contains all the needed Dockerfiles to build Cloudify manager containers.

# How to build images
1. Clone this repository and change your CWD to this directory
1. Install [Docker](https://docs.docker.com/installation/)
1. Install [Docker Compose](http://docs.docker.com/compose/install/)
1. Build `javabase` and `pythonbase` images:

        docker-compose -p cloudify build javabase
        docker-compose -p cloudify build pythonbase

1. Build the rest of the stack:

        docker-compose -p cloudify build


# How to save images to single archive
Save images to tar archive:

    docker save -o <outout_file> cloudify_amqpinflux cloudify_elasticsearch cloudify_fileserver \
                                 cloudify_frontend cloudify_influxdb cloudify_logstash cloudify_mgmtworker \
                                 cloudify_rabbitmq cloudify_restservice cloudify_riemann cloudify_webui

# How to load archive
Load archive on another machine:

    docker load -i <input_file>
