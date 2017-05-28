#!/bin/python

from cloudify import ctx


def upload_keypair(client, local_key_path):
    ctx.logger.info('Uploading key {0}...'.format(local_key_path))
    manager_remote_key_path = '/tmp/mng-key.pem'
    _in, out, _err = client.exec_command('mktemp')
    temp_name = out.read().strip()
    sftp = client.open_sftp()
    sftp.put(local_key_path, temp_name)
    sftp.close()

    client.exec_command('sudo mv {0} {1}'
                        .format(temp_name, manager_remote_key_path))
    ctx.instance.runtime_properties['manager_remote_key_path'] = \
        manager_remote_key_path
