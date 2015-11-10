#!/bin/bash -e

. $(ctx download-resource "components/utils")


PIP_SOURCE_RPM_URL=$(ctx node properties pip_source_rpm_url)
INSTALL_PYTHON_COMPILERS=$(ctx node properties install_python_compilers)

ctx logger info "Installing Python requirements..."
set_selinux_permissive
copy_notice "python"

yum_install ${PIP_SOURCE_RPM_URL}

if [ ! -z "${INSTALL_PYTHON_COMPILERS}" ]; then
    ctx logger info "Installing Compilers..."
    yum_install "python-devel" >/dev/null
    yum_install "gcc" >/dev/null
fi
