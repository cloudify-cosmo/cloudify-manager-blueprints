#!/bin/bash -e

. $(ctx download-resource "components/utils")


export PIP_VERSION=$(ctx node properties pip_version)
export VIRTUALENV_VERSION=$(ctx node properties virtualenv_version)


function install_python
{
    # install prereqs
    sudo yum install yum-downloadonly wget mlocate yum-utils python-devel libyaml-devel ruby rubygems ruby-devel make gcc git -y
    # install python and additions
    # http://bicofino.io/blog/2014/01/16/installing-python-2-dot-7-6-on-centos-6-dot-5/
    sudo yum groupinstall -y 'development tools'
    sudo yum install -y zlib-devel bzip2-devel openssl-devel xz-libs
    sudo mkdir /py27
    cd /py27
    sudo wget http://www.python.org/ftp/python/2.7.6/Python-2.7.6.tar.xz
    sudo xz -d Python-2.7.6.tar.xz
    sudo tar -xvf Python-2.7.6.tar
    cd Python-2.7.6
    sudo ./configure --prefix=/usr
    sudo make
    sudo make altinstall
    # ftp://rpmfind.net/linux/fedora/linux/development/rawhide/x86_64/os/Packages/p/python-2.7.10-1.fc23.x86_64.rpm
}

function install_virtualenv
{
    ctx logger info "Installing Python Requirements..."

    version=${1:-""}

    if [[ ! -z "${version}" ]]; then
        install_module virtualenv==${version} >/dev/null
    else
        install_module virtualenv >/dev/null
    fi
}

function install_pip
{
    version=${1:-""}

    curl --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py >/dev/null | sudo python
    if [[ ! -z "${version}" ]]; then
        install_module "pip==${version} --upgrade" >/dev/null
    fi
}


ctx logger info "Installing Python requirements..."
copy_notice "python"

if [[ ! -z "${PIP_VERSION}" ]]; then
    install_pip ${PIP_VERSION}
else
    install_pip
fi

if [[ ! -z "${VIRTUALENV_VERSION}" ]]; then
    install_virtualenv ${VIRTUALENV_VERSION}
else
    install_virtualenv
fi