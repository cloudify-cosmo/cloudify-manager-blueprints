#! /usr/bin/env bash
set -e

function set_manager_ip() {

  ip=$(/usr/sbin/ip a s | /usr/bin/grep -oE 'inet [^/]+' | /usr/bin/cut -d' ' -f2 | /usr/bin/grep -v '^127.' | /usr/bin/grep -v '^169.254.' | /usr/bin/head -n1)

  echo "Setting manager IP to: ${ip}"

  echo "Updating cloudify-amqpinflux.."
  /usr/bin/sed -i -e "s/AMQP_HOST=.*/AMQP_HOST="'"'"${ip}"'"'"/" /etc/sysconfig/cloudify-amqpinflux
  /usr/bin/sed -i -e "s/INFLUXDB_HOST=.*/INFLUXDB_HOST="'"'"${ip}"'"'"/" /etc/sysconfig/cloudify-amqpinflux

  echo "Updating cloudify-riemann.."
  /usr/bin/sed -i -e "s/RABBITMQ_HOST=.*/RABBITMQ_HOST="'"'"${ip}"'"'"/" /etc/sysconfig/cloudify-riemann
  /usr/bin/sed -i -e "s/REST_HOST=.*/REST_HOST="'"'"${ip}"'"'"/" /etc/sysconfig/cloudify-riemann

  echo "Updating cloudify-mgmtworker.."
  /usr/bin/sed -i -e "s/REST_HOST=.*/REST_HOST="'"'"${ip}"'"'"/" /etc/sysconfig/cloudify-mgmtworker
  /usr/bin/sed -i -e "s/FILE_SERVER_HOST=.*/FILE_SERVER_HOST="'"'"${ip}"'"'"/" /etc/sysconfig/cloudify-mgmtworker
  /usr/bin/sed -i -e "s#MANAGER_FILE_SERVER_URL="'"'"http://.*:53229"'"'"#MANAGER_FILE_SERVER_URL="'"'"http://${ip}:53229"'"'"#" /etc/sysconfig/cloudify-mgmtworker
  /usr/bin/sed -i -e "s#MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL="'"'"http://.*:53229/blueprints"'"'"#MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL="'"'"http://${ip}:53229/blueprints"'"'"#" /etc/sysconfig/cloudify-mgmtworker
  /usr/bin/sed -i -e "s#MANAGER_FILE_SERVER_DEPLOYMENTS_ROOT_URL="'"'"http://.*:53229/deployments"'"'"#MANAGER_FILE_SERVER_DEPLOYMENTS_ROOT_URL="'"'"http://${ip}:53229/deployments"'"'"#" /etc/sysconfig/cloudify-mgmtworker

  echo "Updating logstash.conf.."
  /usr/bin/sed -i -e "s/host => "'"'".*"'"'"/host => "'"'"${ip}"'"'"/" /etc/logstash/conf.d/logstash.conf

  echo "Updating broker_config.json.."
  /usr/bin/sed -i -e "s/"'"'"broker_hostname"'"'": "'"'".*"'"'"/"'"'"broker_hostname"'"'": "'"'"${ip}"'"'"/" /opt/mgmtworker/work/broker_config.json

  echo "Updating broker_ip in provider context.."

  python << END
import requests, json, sys, time
username = "{{ ctx.node.properties.admin_username }}"
password = "{{ ctx.node.properties.admin_password }}"
auth = (username, password)
headers = {"Tenant": "default_tenant", 'Content-Type': 'application/json'}
print('- Getting provider context...')
attempt = 1
while True:
  r = requests.get('http://localhost/api/v3/version', auth=auth, headers=headers)
  if r.status_code == 200:
    print('- REST API is up!')
    break
  if attempt == 10:
    break
  print('- REST API not yet up.. retrying in 5 seconds..')
  time.sleep(5)
  attempt += 1

r = requests.get('http://localhost/api/v3/provider/context', auth=auth, headers=headers)
if r.status_code != 200:
  print("Failed getting provider context.")
  print(r.text)
  sys.exit(1)
response = r.json()
name = response['name']
context = response['context']
context['cloudify']['cloudify_agent']['broker_ip'] = '${ip}'
print('- Updating provider context...')
data = {'name': name, 'context': context}
r = requests.post('http://localhost/api/v3/provider/context', auth=auth, headers=headers, params={'update': 'true'}, data=json.dumps(data))
if r.status_code != 200:
  print("Failed updating provider context.")
  print(r.text)
  sys.exit(1)
END

  echo "Done!"

}

touched_file_path="/opt/cloudify/manager-ip-setter/touched"

if [ ! -f ${touched_file_path} ]; then
  set_manager_ip
  touch ${touched_file_path}
else
  echo "${touched_file_path} exists - not setting manager ip."
fi
