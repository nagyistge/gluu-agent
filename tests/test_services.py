import pytest


@pytest.fixture(scope="session")
def pidfile(request):
    import os
    import tempfile

    _, pidfile = tempfile.mkstemp(suffix=".pid")

    with open(pidfile, "w") as fp:
        fp.write("10000")

    def teardown():
        os.unlink(pidfile)

    request.addfinalizer(teardown)
    return pidfile


@pytest.fixture(scope="session")
def minion_service(pidfile):
    from gluuagent.services import MinionService

    minion = MinionService(pidfile=pidfile)
    return minion


def test_minion_get_pid(minion_service):
    assert minion_service.get_pid() == 10000


def test_minion_no_pid(minion_service, pidfile):
    # temporarily sets invalid pidfile
    minion_service.pidfile = ""
    assert minion_service.get_pid() is None
    # sets a correct pidfile again so other tests don't fail
    minion_service.pidfile = pidfile


def test_minion_is_alive(monkeypatch, minion_service):
    pid = minion_service.get_pid()
    # monkeypatch os.getpgid to return our fake pid
    monkeypatch.setattr("os.getpgid", lambda pid: pid)
    assert minion_service.is_alive(pid) is True


def test_minion_isnot_alive(monkeypatch, minion_service):
    pid = minion_service.get_pid()
    assert minion_service.is_alive(pid) is False


def test_minion_restart(monkeypatch, minion_service):
    monkeypatch.setattr(
        "subprocess.check_output",
        lambda cmd, stderr, shell: True
    )
    assert minion_service.restart() is True


def test_minion_restart_failed(minion_service):
    assert minion_service.restart() is False
