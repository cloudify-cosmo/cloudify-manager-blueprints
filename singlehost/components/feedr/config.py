# flake8: NOQA

# installing feedr
# run pip install feedr
# testing feedr->rabbitmq->logstash->elasticsearch(->kibana) flow
# run fig up -d rabbitmq elasticsearch kibana logstash
# to test the logs queue
# mouth feed -c feedr/config.py -f Log -t AMQP_LOGS -m 100 -b 10 -g 0.5 -v
# to test the events queue
# mouth feed -c feedr/config.py -f Log -t AMQP_EVENTS -m 100 -b 10 -g 0.5 -v
# go to http://ELATICSEARCH_CONTAINER_IP_ADDR:9200/cloudify_events/_search?pretty=true&q=*:*&size=100 to check that documents were posted

# testing feedr->rabbitmq->logstash->influxdb flow
# run mouth feed -c feedr/config.py -f Metric -t AMQP_METRICS -m 100 -b 10 -g 0.5 -v


import uuid

GENERATOR = {
    'formatters': {
        'Log': {
            'type': 'Json',
            'data': {
                'timestamp': ['2015-01-19 21:32:00.000'],
                'uuid': [str(uuid.uuid1()) for i in xrange(3)],
                'level': ['ERROR', 'DEBUG'],
                'name': '$RAND'
            },
            'jsonify': True,
            'stringify': False,
        },
        'Metric': {
            'type': 'Json',
            'data': {
                'points': [[[1.1,4.3,2.1],[1.2,2.0,2.0]]],
                'name': ["web_devweb03_load"],
                'columns': [["min1", "min5", "min15"]]
            },
            'jsonify': True,
            'stringify': False,
        },
        'Custom': {
            'type': 'Custom',
            'format': ['date_time', ' ', 'uuid', ' ', 'level', ': ', 'module', ' - ', 'free_email'],
            'data': {
                'date_time': '$RAND',
                'uuid': [str(uuid.uuid1()) for i in xrange(3)],
                'level': ['ERROR', 'DEBUG', 'INFO', 'CRITICAL'],
                'module': ['module1', 'module2'],
                'free_email': '$RAND'
            }
        }
    },
    'transports': {
        'AMQP_Logs': {
            'type': 'AMQP',
            'host': '172.17.0.123',
            'queue': 'cloudify-logs',
            'exchange': '',
            'routing_key': 'cloudify-logs',
            'durable': True,
            'auto_delete': True,
            'exclusive': False,
            'delivery_mode': 2,
            'exchange_type': 'topic'
        },
        'AMQP_Events': {
            'type': 'AMQP',
            'host': '172.17.0.20',
            'queue': 'cloudify-events',
            'exchange': '',
            'routing_key': 'cloudify-events',
            'durable': True,
            'auto_delete': True,
            'exclusive': False,
            'delivery_mode': 2,
            'exchange_type': 'topic'
        },
        'AMQP_Metrics': {
            'type': 'AMQP',
            'host': '172.17.0.20',
            'queue': '',
            'exchange': 'cloudify-monitoring',
            'routing_key': '*',
            'durable': False,
            'auto_delete': True,
            'exclusive': False,
            'delivery_mode': 2,
            'exchange_type': 'topic'
        },
        "ES": {
            'type': 'Elasticsearch',
            'host': '172.17.0.18',
            'index': 'cloudify_events'
        },
        'InfluxDB': {
            'type': 'InfluxDB',
            'host': '172.17.0.22',
            'user': 'root',
            'password': 'root',
            'database': 'cloudify'
        },
        'UDP': {
            'type': 'UDP',
            'host': '172.17.0.21',
            'port': 9999,
},
    }
}
