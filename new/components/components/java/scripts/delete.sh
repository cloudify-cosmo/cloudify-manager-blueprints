#!/bin/bash

. $(ctx download-resource "components/utils")


JAVA_DOWNLOAD_URL="http://javadl.sun.com/webapps/download/AutoDL?BundleId=106239"


ctx logger info "Uninstalling Java..."

remove_notice "java"

ctx logger info "Downloading java from: ${JAVA_DOWNLOAD_URL}..."
curl --fail -L --silent --header "Cookie: oraclelicense=accept-securebackup-cookie" ${JAVA_DOWNLOAD_URL} --create-dirs -o /tmp/java.rpm >/dev/null
ctx logger info "Installing Java..."
sudo rpm -ivh /tmp/java.rpm >/dev/null