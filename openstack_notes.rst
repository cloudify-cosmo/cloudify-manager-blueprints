`$ neutron port-update 667b0f16-c205-4c14-abb1-b1c0a7392ea7 --allowed_address_pairs list=true type=dict ip_address=172.16.0.200`
`$ neutron port-update  667b0f16-c205-4c14-abb1-b1c0a7392ea7 --admin_state_up=True`


TODO:
    - load-balanced? see the old branch
    - agents key - syncthing
    - syncthing - cleanup (/root)
    - plugins!
    - agents + consul? vs keepalived
    - set_manager_ips - naming/cleanup
    - openstack - lots of 'use existing' flags...
    - multiple DCs?
