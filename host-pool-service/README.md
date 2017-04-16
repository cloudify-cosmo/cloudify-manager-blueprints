Information about installing only the Host pool service
=======================================================

It is invalid to run `bootstrap` subcommand and end up without a working
manager, so any attempt to bootstrap `only-host-pool.yaml` blueprint will
result in an obvious failure.

To perform this process successfully use Cloudify shell's `local` subcommand,
for example:

1.  `cfy local install-plugins -p /path/to/blueprint.yaml`
2.  `cfy local init -p /path/to/blueprint.yaml -i /path/to/inputs.yaml`
3.  `cfy local execute -w install`
4.  `cfy local execute -w uninstall`
