#!/bin/bash

. $(ctx download-resource "components/utils")

JAVA_SOURCE_URL=$(ctx node properties java_rpm_source_url)


ctx logger info "Installing Java..."
set_selinux_permissive
copy_notice "java"

if [[ "$JAVA_SOURCE_URL" == *rpm ]]; then
    yum_install ${JAVA_SOURCE_URL}
else
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
fi
