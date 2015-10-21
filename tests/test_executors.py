import pytest


def test_run_docker_exec(monkeypatch, docker_client):
    from gluuagent.executors import run_docker_exec

    monkeypatch.setattr(
        "docker.Client.exec_create",
        lambda cls, container, cmd: {"Id": "random-id"}
    )
    monkeypatch.setattr(
        "docker.Client.exec_start",
        lambda cls, exec_cmd: "",
    )
    monkeypatch.setattr(
        "docker.Client.exec_inspect",
        lambda cls, exec_cmd: {"ExitCode": 0},
    )

    result = run_docker_exec(docker_client, "random-id", "echo foobar")
    assert result.exit_code == 0


@pytest.mark.parametrize("exit_code", [0, 1])
def test_oxauth_entrypoint(monkeypatch, docker_client, db, oxauth_node,
                           master_provider, cluster, exit_code):
    from gluuagent.executors import DockerExecResult
    from gluuagent.executors import OxauthExecutor

    exec_result = DockerExecResult("echo test", exit_code, "test")
    monkeypatch.setattr(
        "gluuagent.executors.run_docker_exec",
        lambda client, node_id, cmd: exec_result,
    )
    monkeypatch.setattr(
        "docker.Client.stop",
        lambda cls, container: None,
    )
    executor = OxauthExecutor(oxauth_node, master_provider, cluster,
                              docker_client, db)
    executor.run_entrypoint()


@pytest.mark.parametrize("exit_code", [0, 1])
def test_oxtrust_entrypoint(monkeypatch, docker_client, db, oxtrust_node,
                            master_provider, cluster, exit_code):
    from gluuagent.executors import DockerExecResult
    from gluuagent.executors import OxtrustExecutor

    exec_result = DockerExecResult("echo test", exit_code, "test")
    monkeypatch.setattr(
        "gluuagent.executors.run_docker_exec",
        lambda client, node_id, cmd: exec_result,
    )
    monkeypatch.setattr(
        "docker.Client.stop",
        lambda cls, container: None,
    )
    executor = OxtrustExecutor(oxtrust_node, master_provider, cluster,
                               docker_client, db)
    executor.run_entrypoint()


def test_httpd_entrypoint(monkeypatch, docker_client, db, httpd_node,
                          master_provider, cluster):
    from gluuagent.executors import HttpdExecutor
    executor = HttpdExecutor(httpd_node, master_provider, cluster,
                             docker_client, db)
    executor.run_entrypoint()
