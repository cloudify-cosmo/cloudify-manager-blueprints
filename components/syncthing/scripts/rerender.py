#!/usr/bin/env python

import json

import xml.etree.ElementTree as ET
import urllib2


tree = ET.parse('/root/.config/syncthing/config.xml')
apikey = tree.findall('.//gui/apikey')[0].text
headers = {'X-Api-Key': apikey}


def request(url, data=None, method='GET', parse_json=True):
    req = urllib2.Request(url, data=data, headers=headers)
    req.get_method = lambda: method
    resp = urllib2.urlopen(req)
    if parse_json:
        return json.load(resp)
    return resp.read()


status = request('http://127.0.0.1:8384/rest/system/status')
my_id = status['myID']
config = request('http://127.0.0.1:8384/rest/system/config')

config['options']['listenAddresses'] = ['tcp://0.0.0.0']

devices = []

nodes_resp = urllib2.urlopen('http://127.0.0.1:8500/v1/kv/syncthing?recurse')
nodes_data = json.load(nodes_resp)


for node in nodes_data:
    line = node['Value'].decode('base64').strip()
    if line:
        node_id, addr, name = line.strip().split(',')
        if node_id != my_id:
            devices.append({
                'deviceID': node_id,
                'addresses': [addr],
                'name': name
            })

config['devices'] = devices
config['folders'] = [
    {
        'id': 'resources-1',
        'path': '/opt/manager/resources',
        'rescanIntervalS': 15,
        'devices': [{'deviceID': d['deviceID']} for d in devices]
    },
    {
        'id': 'mgmtworker-env-1',
        'path': '/opt/mgmtworker/env/lib',
        'rescanIntervalS': 30,
        'devices': [{'deviceID': d['deviceID']} for d in devices]
    }
]

print config
print request('http://127.0.0.1:8384/rest/system/config',
              data=json.dumps(config), method='POST', parse_json=False)
