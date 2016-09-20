#!/usr/bin/env python
#########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

import sys
import yaml
import json

from flask import Flask
from flask_security import Security

from manager_rest.storage.models import db, Tenant
from manager_rest.security import user_datastore
from manager_rest.utils import add_users_and_roles_to_userstore


def _get_flask_app(config):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        'postgresql://{0}:{1}@{2}/{3}'.format(
            'cloudify',
            'cloudify',
            config['postgresql_host'],
            config['postgresql_db_name']
        )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app


def _add_users_and_roles(config):
    # Need to load security_configuration with a yaml loader, as it's a string
    security_config = yaml.load(config['security_configuration'])
    userstore = security_config.get('userstore', {})
    add_users_and_roles_to_userstore(
        user_datastore,
        users=userstore.get('users', []),
        roles=userstore.get('roles', [])
    )


def _create_db_tables(config):
    app = _get_flask_app(config)
    Security(app=app, datastore=user_datastore)
    with app.app_context():
        db.init_app(app)
        db.create_all()
    app.app_context().push()


def _add_default_tenant():
    t = Tenant(name='default_tenant')
    db.session.add(t)
    db.session.commit()


if __name__ == '__main__':
    # We're expecting to receive as an argument the path to the config file
    assert len(sys.argv) == 2, 'No config file path was provided'
    with open(sys.argv[1], 'r') as f:
        config = json.load(f)

    print 'Creating tables in the DB'
    _create_db_tables(config)
    print 'Tables created successfully'

    print 'Adding default tenant'
    _add_default_tenant()
    print 'Tables created successfully'

    print 'Adding users and roles to the DB'
    _add_users_and_roles(config)
    print 'Users and roles added successfully'
