import fabric


def configure(vcloud_config):
    _update_container()


def _update_container():
    """ install some packeges for future deployments creation """
    # update system to last version
    fabric.api.run("sudo docker exec -i -t cfy apt-get "
                   "update -q -y 2>&1")
    fabric.api.run("sudo docker exec -i -t cfy apt-get "
                   "dist-upgrade -q -y 2>&1")
    # install:
    fabric.api.run("sudo docker exec -i -t cfy apt-get "
                   "install gcc python-dev libxml2-dev libxslt-dev "
                   "zlib1g-dev -q -y 2>&1")
