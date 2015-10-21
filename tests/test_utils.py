import pytest


@pytest.mark.parametrize("logfile", [
    None,
    "/tmp/test-gluu-agent.log",
])
def test_get_logger(logfile):
    from gluuagent.utils import get_logger
    assert get_logger(logfile)


def test_decrypt_text():
    from gluuagent.utils import decrypt_text

    key = "123456789012345678901234"
    enc_text = "im6yqa0BROeTNcwvx4XCaw=="
    assert decrypt_text(enc_text, key) == "password"


def test_expose_cidr():
    from gluuagent.utils import expose_cidr

    ipnet = "10.1.1.0/24"
    assert expose_cidr(ipnet) == ("10.1.1.254", 24)
