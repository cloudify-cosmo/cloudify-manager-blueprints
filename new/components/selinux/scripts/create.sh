#!/bin/bash -e

. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/selinux/config"

export SELINUX_ENFORCING="$(ctx -j node properties selinux_enforcing)"

# Ensure log directories exist before we start (they may be needed here and will be needed elsewhere)
create_dir /var/log/cloudify

if [[ "${SELINUX_ENFORCING}" == 'true' ]]; then
  # Make SELinux enforce policy
  ctx instance runtime_properties selinux_mode enforcing

  # Apply the change without a reboot
  sudo setenforce 1

  # Install required tools for managing SELinux
  yum_install "policycoreutils-python" >/dev/null
  yum_install "selinux-policy-devel" >/dev/null

  # Ensure general SELinux policies are set that apply across most applications
  sudo semanage fcontext -a -s system_u -t var_log_t '/var/log/cloudify(/.*)?'
  sudo restorecon -F -R -v /var/log/cloudify
else
  # Make SELinux only log violations of policy
  # This is preferred to 'disabled' as it allows enabling without a reboot if so desired later
  ctx instance runtime_properties selinux_mode permissive

  # Apply the change without a reboot
  sudo setenforce 0
fi

# Persist the setting after reboot
deploy_blueprint_resource "${CONFIG_REL_PATH}/config" "/etc/selinux/config"
sudo chown root.root /etc/selinux/config
sudo chmod 644 /etc/selinux/config
