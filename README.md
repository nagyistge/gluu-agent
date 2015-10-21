# gluu-agent

A tool to ensure provider is reachable within cluster

## Installation

```
apt-get install -y swig libssl-dev python-dev lxc-docker-1.6.2
git clone git://github.com/GluuFederation/gluu-agent.git
cd gluu-agent
python setup.py install
```

## Testing

Testcases are running using ``pytest`` executed by ``tox``.

```
pip install tox
tox
```

See `tox.ini` for details.
