#!/usr/bin/env python

import subprocess
import os
import importlib

subprocess.check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')

ctx.logger.info('Starting Riemann Service...')
utils.systemd.start('riemann')
