#!/usr/bin/env python2

import os
import shutil
import argparse

HOME_DIR = "{{ ctx.instance.runtime_properties.home_dir}}"


def _restore(snapshot_root):
    for folder in ['conf', 'dist/widgets', 'dist/templates']:
        destination = os.path.join(HOME_DIR, folder, 'from_snapshot')
        if os.path.exists(destination):
            # This shouldn't exist as we don't support restoring on a non-empty
            # manager, but we'll carry on the convention of squashing what is
            # present if something is in the way (see DB restore's DROP)
            shutil.rmtree(destination)
        shutil.copytree(os.path.join(snapshot_root, folder), destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot_root')
    args = parser.parse_args()
    _restore(args.snapshot_root)
