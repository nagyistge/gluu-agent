# gluu-agent

A tool to ensure provider is reachable within cluster

## Features

1.  **Self-recovery**

    Recover all nodes deployed to the provider where `gluu-agent`
    is installed to. The recovery process is automatically
    executed after reboot via init script. To run the recovery
    process manually:

        gluu-agent recover

    This process requires a local cluster data; by default located
    at `/var/lib/gluu-cluster/db/db.json`.

    To see all available options for `recover` command:

        gluu-agent recover --help

## Installation

```
apt-get install -y swig libssl-dev python-dev docker-engine
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
