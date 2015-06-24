#!/bin/bash

. $(ctx download-resource "components/utils")


JAVA_DOWNLOAD_URL="http://javadl.sun.com/webapps/download/AutoDL?BundleId=106239"


ctx logger info "Installing Java..."

copy_notice "java"

# alternative tar based oracle jre installation. deprecated.
# export JAVABASE_VERSION=7u76
# export DOCKER_ENV=False
# export JAVA_HOME=/opt/java
# sudo curl --fail --location --header "Cookie: oraclelicense=accept-securebackup-cookie" --create-dirs -o /tmp/java.tar.gz http://download.oracle.com/otn-pub/java/jdk/${JAVABASE_VERSION}-b13/jre-${JAVABASE_VERSION}-linux-x64.tar.gz &&
# sudo mkdir ${JAVA_HOME} && sudo tar -xzvf /tmp/java.tar.gz -C ${JAVA_HOME} --strip=1 &&

ctx logger info "Downloading java from: ${JAVA_DOWNLOAD_URL}..."
curl --fail -L --silent --header "Cookie: oraclelicense=accept-securebackup-cookie" ${JAVA_DOWNLOAD_URL} --create-dirs -o /tmp/java.rpm >/dev/null
ctx logger info "Installing Java..."
sudo rpm -ivh /tmp/java.rpm >/dev/null