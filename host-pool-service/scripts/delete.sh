#!/bin/bash


_error(){
    echo "$1" 1>&2
    exit 1
}


[ $# -lt 1 ] && _error "Missing argument."

declare -r _host_pool_dir=$1

shift
[ $# -gt 0 ] && _error "Unexpected arguments: '$@'."

[ -d "${_host_pool_dir}" ] || \
    _error "Host pool's directory '${_host_pool_dir}' does not exist!"

rm -rvf "${_host_pool_dir}"
