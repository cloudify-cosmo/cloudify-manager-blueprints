#!/bin/bash


function import_helpers
{
    if [ ! -e "/tmp/utils" ]; then
        cp components/utils /tmp/utils
        # ctx download-resource "components/utils" '@{"target_path": "/tmp/utils"}'
    fi
    . /tmp/utils
    # required only in current vagrant environment otherwise passed to the vm via the script plugin
    . components/env_vars
}

function main
{
    log_section "Installing Java..."

    copy_notice "java" &&

    # export JAVABASE_VERSION=7u76
    # export DOCKER_ENV=False
    # export JAVA_HOME=/opt/java
    # sudo curl --fail --location --header "Cookie: oraclelicense=accept-securebackup-cookie" --create-dirs -o /tmp/java.tar.gz http://download.oracle.com/otn-pub/java/jdk/${JAVABASE_VERSION}-b13/jre-${JAVABASE_VERSION}-linux-x64.tar.gz &&
    # sudo mkdir ${JAVA_HOME} && sudo tar -xzvf /tmp/java.tar.gz -C ${JAVA_HOME} --strip=1 &&
    sudo curl --fail --location --header "Cookie: oraclelicense=accept-securebackup-cookie" http://javadl.sun.com/webapps/download/AutoDL?BundleId=106239 --create-dirs -o /tmp/java.rpm && \
    sudo rpm -ivh /tmp/java.rpm && \
    clean_tmp
}

cd /vagrant
import_helpers
main