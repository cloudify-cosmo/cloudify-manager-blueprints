#!/opt/manager/env/bin/python

import json
import sys

import xml.etree.ElementTree as ET
import urllib2


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
config = json_request('http://127.0.0.1:8384/rest/system/config')

config['options']['listenAddresses'] = ['tcp://0.0.0.0']

devices = []
try:
    nodes = open('/opt/cloudify/syncthing/syncthings.csv')
except IOError:
    sys.exit(0)

with nodes as f:
    for line in f:
        if line.strip():
            node_id, addr, name = line.strip().split(',')
            if node_id != my_id:
                devices.append({
                    'deviceID': node_id,
                    'addresses': [addr],
                    'name': name
                })

config['devices'] = devices
config['folders'] = [{
    'id': 'resources-1',
    'path': '/opt/manager/resources',
    'rescanIntervalS': 15,
    'devices': [{'deviceID': d['deviceID']} for d in devices]
}]

json_request('http://127.0.0.1:8384/rest/system/config',
             data=json.dumps(config), method='POST')
