#!/usr/bin/env python

import json
import tempfile

import xml.etree.ElementTree as ET
import urllib2

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


SYNCTHING_SERVICE_NAME = 'syncthing'

utils.start_service(SYNCTHING_SERVICE_NAME)
utils.systemd.enable(SYNCTHING_SERVICE_NAME)
utils.systemd.verify_alive(SYNCTHING_SERVICE_NAME)

utils.deploy_blueprint_resource(
    'components/syncthing/scripts/rerender.py',
    '/opt/cloudify/syncthing/rerender.py',
    SYNCTHING_SERVICE_NAME,
    render=False
)
utils.chmod('+x', '/opt/cloudify/syncthing/rerender.py')

consul_syncthing_config = {
    'watches': [
        {
            'type': 'keyprefix',
            'prefix': 'syncthing/',
            'handler': '/opt/cloudify/syncthing/rerender.py'
        }
    ]
}

with tempfile.NamedTemporaryFile(delete=False) as f:
    json.dump(consul_syncthing_config, f)

utils.move(f.name, '/etc/consul.d/syncthing.json')
utils.systemd.restart('consul')

# XXX
utils.sudo('chmod a+rX -R /root')
tree = ET.parse('/root/.config/syncthing/config.xml')
apikey = tree.findall('.//gui/apikey')[0].text
headers = {'X-Api-Key': apikey}


def json_request(url, data=None, method='GET'):
    req = urllib2.Request(url, data=data, headers=headers)
    req.get_method = lambda: method
    resp = urllib2.urlopen(req)
    return json.load(resp)


status = json_request('http://127.0.0.1:8384/rest/system/status')
my_id = status['myID']

utils.run([
    'curl',
    '-XPUT',
    '-d',
    '{0},tcp://{1},{2}'.format(my_id, ctx.instance.host_ip, ctx.instance.id),
    'http://{0}:8500/v1/kv/syncthing/{1}'.format(
        ctx.instance.host_ip, ctx.instance.id),
])
