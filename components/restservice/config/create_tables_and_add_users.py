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

from manager_rest.storage import user_datastore
from manager_rest.storage.models import db, Tenant
from manager_rest.constants import DEFAULT_TENANT_NAME
from manager_rest.utils import create_security_roles_and_admin_user


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
    app.config['SECURITY_USER_IDENTITY_ATTRIBUTES'] = 'username, email'
    return app


def _create_security_roles_and_admin_user(config, default_tenant):
    print 'Creating security roles and admin user'
    security_config = yaml.load(config['security_configuration'])
    create_security_roles_and_admin_user(
        user_datastore,
        admin_username=security_config['admin_username'],
        admin_password=security_config['admin_password'],
        default_tenant=default_tenant
    )
    print 'Security roles and admin user created successfully'


def _create_db_tables(config):
    print 'Creating tables in the DB'
    app = _get_flask_app(config)
    Security(app=app, datastore=user_datastore)
    with app.app_context():
        db.init_app(app)
        db.create_all()
    app.app_context().push()
    print 'Tables created successfully'


def _add_default_tenant():
    print 'Adding default tenant ' + DEFAULT_TENANT_NAME
    default_tenant = Tenant(name=DEFAULT_TENANT_NAME)
    db.session.add(default_tenant)
    db.session.commit()
    print 'Default tenant created successfully'
    return default_tenant


if __name__ == '__main__':
    # We're expecting to receive as an argument the path to the config file
    assert len(sys.argv) == 2, 'No config file path was provided'
    with open(sys.argv[1], 'r') as f:
        config = json.load(f)
    _create_db_tables(config)
    default_tenant = _add_default_tenant()
    _create_security_roles_and_admin_user(config, default_tenant)
