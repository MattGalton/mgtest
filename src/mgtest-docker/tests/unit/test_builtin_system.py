from __future__ import annotations

import json
import socket
import subprocess
from types import SimpleNamespace

from mgtest.engine.builtin.tests.command.spec import Command
from mgtest.engine.builtin.tests.file_matches.spec import FileMatches
from mgtest.engine.builtin.tests.http_request.spec import HttpRequest
from mgtest.engine.builtin.tests.tcp_connect.spec import TcpConnect


def run(spec):
    instance = spec.create_instance()
    instance.run({})
    return instance.outputs


def test_python_command_captures_output_and_file_matches_reads_content(tmp_path):
    output = run(
        Command(
            type="Command",
            name="command",
            python_command="print('hello from command')",
            stdout_contains="hello from command",
        )
    )
    assert output.exit_code == 0
    assert output.stdout == "hello from command\n"

    output = run(
        Command(
            type="Command",
            name="shell-command",
            shell_command="printf 'hello from shell'",
            stdout_contains="hello from shell",
        )
    )
    assert output.stdout == "hello from shell"

    path = tmp_path / "example.txt"
    path.write_text("first line\nsecond line\n")
    output = run(
        FileMatches(
            type="FileMatches",
            name="file",
            path=path,
            contains="second",
            matches=r"first line\nsecond",
        )
    )
    assert output.content == "first line\nsecond line\n"


def test_tcp_connect_retries_connection_errors(monkeypatch):
    attempts = 0

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    def create_connection(address, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionRefusedError
        return Connection()

    monkeypatch.setattr(socket, "create_connection", create_connection)
    assert run(
        TcpConnect(
            type="TcpConnect", name="tcp", host="127.0.0.1", port=8080, timeout=1, interval=0.001
        )
    ).connected
    assert attempts == 2


def test_http_request_retries_and_exposes_structured_response(monkeypatch):
    from mgtest.engine.builtin.tests.http_request import instance

    attempts = 0

    class Response:
        status = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self):
            return json.dumps({"status": "ready"}).encode()

    def urlopen(request, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("not ready")
        return Response()

    monkeypatch.setattr(instance, "urlopen", urlopen)
    output = run(
        HttpRequest(
            type="HttpRequest",
            name="http",
            url="http://service.test/health",
            json_equals={"status": "ready"},
            interval=0.001,
        )
    )
    assert output.status == 200
    assert output.json_data == {"status": "ready"}
    assert attempts == 2


def test_docker_container_runs_with_environment_and_published_ports(monkeypatch):
    from mgtest_docker.resources.docker_container import instance
    from mgtest_docker.resources.docker_container.spec import DockerContainer

    commands = []

    def docker_run(command, **kwargs):
        commands.append(command)
        if command[:3] == ["docker", "run", "--detach"]:
            return subprocess.CompletedProcess(command, 0, "container-id\n", "")
        if command[:2] == ["docker", "port"]:
            return subprocess.CompletedProcess(command, 0, "8080/tcp -> 0.0.0.0:49152\n", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(instance.subprocess, "run", docker_run)
    spec = DockerContainer(
        type="DockerContainer",
        name="api",
        image="example/api:latest",
        command=["serve"],
        environment={"MODE": "test"},
        ports={8080: None},
    )
    resource = spec.create_instance()
    resource.setup()
    assert resource.outputs.container_id == "container-id"
    assert resource.outputs.ports == {8080: 49152}
    assert commands[0] == [
        "docker",
        "run",
        "--detach",
        "--env",
        "MODE=test",
        "--publish",
        "0:8080",
        "example/api:latest",
        "serve",
    ]
    resource.teardown()
    assert commands[-1] == ["docker", "rm", "--force", "container-id"]


def test_docker_compose_and_git_repository_build_lifecycle_commands(monkeypatch, tmp_path):
    from mgtest.engine.builtin.resources.git_repository import instance as git_instance
    from mgtest.engine.builtin.resources.git_repository.spec import GitRepository
    from mgtest_docker.resources.docker_compose import instance as compose_instance
    from mgtest_docker.resources.docker_compose.spec import DockerCompose

    compose_commands = []

    def compose_run(command, **kwargs):
        compose_commands.append(command)
        stdout = "container-one\n" if command[-2:] == ["ps", "--quiet"] else ""
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(compose_instance.subprocess, "run", compose_run)
    compose = DockerCompose(
        type="DockerCompose",
        name="stack",
        files=[tmp_path / "compose.yaml"],
        project_name="example",
        services=["api"],
    ).create_instance()
    compose.setup()
    assert compose.outputs.containers == ["container-one"]
    compose.teardown()
    assert compose_commands[0][-3:] == ["up", "--detach", "api"]
    assert compose_commands[-1][-2:] == ["down", "--volumes"]

    git_commands = []

    def git_run(command, **kwargs):
        git_commands.append(command)
        stdout = "abc123\n" if command[1:3] == ["rev-parse", "HEAD"] else ""
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(git_instance.subprocess, "run", git_run)
    path = tmp_path / "checkout"
    repository = GitRepository(
        type="GitRepository",
        name="source",
        url="https://example.test/source.git",
        path=path,
        ref="v1.0",
        depth=1,
        submodules=True,
    ).create_instance()
    repository.setup()
    assert repository.outputs.path == path
    assert repository.outputs.revision == "abc123"
    assert git_commands[0] == [
        "git",
        "clone",
        "--depth",
        "1",
        "https://example.test/source.git",
        str(path),
    ]
    assert ["git", "checkout", "--force", "v1.0"] in git_commands


def test_git_repository_uses_the_active_workspace_mirror(monkeypatch, tmp_path):
    from mgtest.engine.builtin.resources.git_repository import instance as git_instance
    from mgtest.engine.builtin.resources.git_repository.spec import GitRepository
    from mgtest.runtime import RunWorkspace

    commands = []

    def git_run(command, **kwargs):
        commands.append(command)
        stdout = "abc123\n" if command[1:3] == ["rev-parse", "HEAD"] else ""
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(git_instance.subprocess, "run", git_run)
    workspace = RunWorkspace.create(tmp_path, SimpleNamespace(definitions={}, test_order=()))
    repository = GitRepository(
        type="GitRepository",
        name="source",
        url="https://example.test/source.git",
        path=tmp_path / "checkout",
    ).create_instance()
    with workspace.active():
        repository.setup()
    assert commands[0][:3] == ["git", "clone", "--mirror"]
    assert "--reference-if-able" in commands[1]
