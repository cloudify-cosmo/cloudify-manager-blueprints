#! /bin/bash -e

CURR_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PLUGINS_BRANCH=$2
CORE_BRANCH=$3

build_cloudify_images()
{
  pushd $CURR_DIR
    # docker build sometimes fails. Retry
    echo building javabase image
    for i in 1 2 3 4 5 6
    do
      sudo docker-compose -p cloudify build javabase && break || sleep 2;
    done
    echo building pythonbase image
    for i in 1 2 3 4 5 6
    do
      sudo docker-compose -p cloudify build pythonbase && break || sleep 2;
    done
    echo building cloudify images
    for i in 1 2 3 4 5 6 7 8 9 10 11 12
    do
      sudo docker-compose -p cloudify build && break || sleep 2;
    done
  popd
}

modify_dockerfiles()
{
  FILES=$(find $CURR_DIR -name "Dockerfile" -print)
  for file in $FILES
  do
    sed -i 's/DSL_VERSION=master/DSL_VERSION='"$CORE_BRANCH"'/g' $file
    sed -i 's/REST_CLIENT_VERSION=master/REST_CLIENT_VERSION='"$CORE_BRANCH"'/g' $file
    sed -i 's/COMMON_VERSION=master/COMMON_VERSION='"$CORE_BRANCH"'/g' $file
    sed -i 's/MANAGER_VERSION=master/MANAGER_VERSION='"$CORE_BRANCH"'/g' $file
    sed -i 's/REST_VERSION=master/REST_VERSION='"$CORE_BRANCH"'/g' $file
    sed -i 's/AMQP_INFLUX_VERSION=master/AMQP_INFLUX_VERSION='"$CORE_BRANCH"'/g' $file
    sed -i 's/WEBUI_VERSION=master/WEBUI_VERSION='"$CORE_BRANCH"'/g' $file
    sed -i 's/SCRIPT_VERSION=master/SCRIPT_VERSION='"$PLUGINS_BRANCH"'/g' $file
  done

}

enable_docker_api()
{
  sudo /bin/sh -c 'echo DOCKER_OPTS=\"-H tcp://127.0.0.1:4243 -H unix:///var/run/docker.sock\" >> /etc/default/docker'
  sudo restart docker
  export DOCKER_HOST=tcp://localhost:4243
}

build_images()
{
  DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

  echo setting plugin version to $PLUGINS_BRANCH and core version to $CORE_BRANCH
  modify_dockerfiles $PLUGINS_BRANCH $CORE_BRANCH

  echo enabling Docker API
  enable_docker_api

  echo Building cloudify stack image.
  build_cloudify_images
}

main()
{
  build_images
}

main