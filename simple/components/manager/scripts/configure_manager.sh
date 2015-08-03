#!/bin/bash -e

. $(ctx download-resource "components/utils")


function _post_provider_context() {
    export PROVIDER_CONTEXT_FILE=$(ctx download-resource "components/manager/config/provider_context")
    export PROVIDER_CONTEXT_DATA=$(cat $PROVIDER_CONTEXT_FILE)

    ctx instance runtime_properties manager_provider_context "$PROVIDER_CONTEXT_DATA"

    ctx logger info "Posting Provider Context..."
    curl --fail --silent --request POST --data @${PROVIDER_CONTEXT_FILE} http://localhost/provider/context --header "Content-Type:application/json" >/dev/null
}


function _disable_requiretty() {
    ###
    # disables requiretty for a user or globally
    # NOTE THAT THIS SCRIPT MUST RUN WITH A TTY or via ssh -t
    ###

    function get_distro() {
        ###
        # potentially, we would grep whether 'ID=distro' is in /etc/os-release
        # but apparently this is only supported on systemd based systems.
        # for now, this will have to do. yuch.
        # if we decide to change this:
        # http://0pointer.de/blog/projects/os-release.html
        ###
        if grep -i 'centos' /proc/version > /dev/null; then
            echo 'supported'
        elif grep -i 'ubuntu' /proc/version > /dev/null; then
            echo 'supported'
        elif grep -i 'redhat' /proc/version > /dev/null; then
            echo 'supported'
        elif grep -i 'debian' /proc/version > /dev/null; then
            echo 'supported'
        else
            echo 'unsupported'
        fi
    }

    function disable_for_user() {
        ###
        # Disables requiretty for a specific user ${whoami}.
        # by creating a user specific /etc/sudoers.d file and applying the directive for it.
        ###
        if sudo grep -q -E '[^!]requiretty' /etc/sudoers; then
            echo "Creating sudoers user file and setting disable requiretty directive."
            echo "Defaults:${whoami} ${requiretty}" | sudo tee /etc/sudoers.d/${whoami} >/dev/null
            sudo chmod 0440 /etc/sudoers.d/${whoami}
        else
            echo "No requiretty directive found, nothing to do."
        fi
    }

    function disable_for_all_users() {
        ###
        # Disables requiretty for all users by modifying the /etc/sudoers file.
        ###
        if [ ! -f "/etc/sudoers" ]; then
            error_exit 116 "Could not find sudoers file at expected location (/etc/sudoers)"
        fi
        echo "Setting directive in /etc/sudoers."
        sudo sed -i 's/^Defaults.*requiretty/#&/g' /etc/sudoers || error_exit_on_level $? 117 "Failed to edit sudoers file to disable requiretty directive" 1
    }

    # http://unix.stackexchange.com/questions/6345/how-can-i-get-distribution-name-and-version-number-in-a-simple-shell-script
    whoami=$(whoami)
    requiretty='!requiretty'

    # for supported distros, this will disable requiretty for a specific user.
    # Otherwise, it will disable it for all users.
    if [ "$(get_distro)" != 'unsupported' ]; then
        echo "Distro is supported."
        disable_for_user
    else
        echo "Distro is unsupported."
        disable_for_all_users
    fi
}

# REMOVE, TEST ONLY!
# test for when requiretty is enabled and the disable-requiretty script should disable it.
replace "#Defaults requiretty" "Defaults requiretty" "/etc/sudoers"


_post_provider_context
_disable_requiretty