#!/usr/bin/env python2

import os
import shutil
import argparse

HOME_DIR = "{{ ctx.instance.runtime_properties.home_dir}}"


def _restore(snapshot_root, override=False):
    for folder in ['conf', 'dist/widgets', 'dist/templates']:
        destination = os.path.join(HOME_DIR, folder)
        if not override:
            destination = os.path.join(destination, 'from_snapshot')
        if os.path.exists(destination):
            shutil.rmtree(destination)
        shutil.copytree(os.path.join(snapshot_root, folder), destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot_root')
    parser.add_argument(
        '--override-existing',
        action='store_true',
        help='Override the existing stage files with the restored files.',
    )
    args = parser.parse_args()
    _restore(args.snapshot_root, override=args.override_existing)
