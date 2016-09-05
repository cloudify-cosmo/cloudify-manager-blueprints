#!/bin/bash

set -e

function update_ps_configuration() {
    ctx logger info "Updating Configuration..."
    pg_hba="/var/lib/pgsql/9.5/data/pg_hba.conf"
    sudo cp $pg_hba $pg_hba.backup
    ctx logger debug "Modifying $pg_hba"
    awk_replace="/^[host|local]/{gsub(/ident/, \"md5\")}; {print}"
    sudo bash -c "cat $pg_hba | awk '${awk_replace}' > ${pg_hba}.tmp; cp ${pg_hba}.tmp ${pg_hba}"
}

update_ps_configuration
