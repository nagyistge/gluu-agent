import pytest


@pytest.mark.parametrize("logfile", [
    None,
    "/tmp/test-gluu-agent.log",
])
def test_get_logger(logfile):
    from gluuagent.utils import get_logger
    assert get_logger(logfile)
