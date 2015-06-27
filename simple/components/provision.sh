#!/bin/bash

function update_local_cache
{
    sudo yum -y update
}


update_local_cache
sudo yum install python-devel g++ gcc -y

curl --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo python
sudo pip install virtualenv
virtualenv cfy
source cfy/bin/activate
pip install cloudify==3.2

# wget http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/get-cloudify.py
# python get-cloudify.py -v -f

sudo mkdir /root/.ssh
ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
sudo cp ~/.ssh/id_rsa /root/.ssh/id_rsa