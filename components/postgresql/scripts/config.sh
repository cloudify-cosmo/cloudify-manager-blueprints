#!/bin/bash

set -e

function update_ps_configuration() {
    ctx logger info "Updating Configuration..."
    pg_hba="/var/lib/pgsql/9.5/data/pg_hba.conf"
    cp $pg_hba $pg_hba.backup
    awk_replace="/^host/{gsub(/ident/, \"md5\")}; {print}"
    bash -c "cat $pg_hba | awk '${awk_replace}' > ${pg_hba}.tmp; cp ${pg_hba}.tmp ${pg_hba}"
}

update_ps_configuration
