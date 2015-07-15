#!/bin/bash

cat /vagrant/test_public_key.pub >> ~/.ssh/authorized_keys
sudo cp /vagrant/test_public_key.pub ~/.ssh/test_public_key.pub