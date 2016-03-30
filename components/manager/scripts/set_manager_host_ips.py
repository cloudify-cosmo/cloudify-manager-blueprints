from cloudify import ctx
from cloudify.state import ctx_parameters as inputs

# TODO: ask NirC if this is ok
ctx.logger.info('Setting Private Manager IP Runtime Property.')
manager_private_ip = ctx.source.instance.host_ip
ctx.logger.info('Manager Private IP is: {0}'.format(manager_private_ip))

ctx.logger.info('Setting Public Manager IP Runtime Property.')
manager_ip = inputs['public_ip']
ctx.logger.info('Manager Public IP is: {0}'.format(manager_ip))
ctx.source.instance.runtime_properties['public_ip'] = manager_ip

manager_public_ip = ctx.source.instance.runtime_properties['public_ip']
ctx.logger.info('Manager public IP is: {0}'.format(manager_public_ip))
# ctx.target.instance.runtime_properties['manager_host_ip'] = manager_private_ip
ctx.target.instance.runtime_properties['manager_host_ip'] = manager_public_ip