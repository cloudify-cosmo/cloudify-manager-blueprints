#!/bin/python

import json
import sys
import time

import requests


def update_provider_context(manager_ip):
    username = "{{ ctx.node.properties.admin_username }}"
    password = "{{ ctx.node.properties.admin_password }}"
    auth = (username, password)
    headers = {"Tenant": "default_tenant", 'Content-Type': 'application/json'}
    print('- Getting provider context...')
    attempt = 1
    while True:
        try:
            r = requests.get(
                'http://localhost/api/version', auth=auth, headers=headers)
            if r.status_code == 200:
                print('- REST API is up!')
                break
            if attempt == 10:
                break
        except Exception as e:
            print('- Error accessing REST API: {}'.format(e))
        print('- REST API not yet up.. retrying in 5 seconds..')
        time.sleep(5)
        attempt += 1

    r = requests.get(
        'http://localhost/api/v3.1/provider/context',
        auth=auth, headers=headers)
    if r.status_code != 200:
        print("Failed getting provider context.")
        print(r.text)
        sys.exit(1)
    response = r.json()
    name = response['name']
    context = response['context']
    context['cloudify']['cloudify_agent']['broker_ip'] = manager_ip
    print('- Updating provider context...')
    data = {'name': name, 'context': context}
    r = requests.post(
        'http://localhost/api/v3.1/provider/context',
        auth=auth, headers=headers,
        params={'update': 'true'},
        data=json.dumps(data))
    if r.status_code != 200:
        print("Failed updating provider context.")
        print(r.text)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Expected 1 argument - <manager-ip>')
        print('Provided args: {0}'.format(sys.argv[1:]))
        sys.exit(1)
    update_provider_context(sys.argv[1])
