import sys

from mgtest.engine.builtin.resources.executable.executable import Executable


def test_executable_run_wait():
    with Executable(sys.executable, ["-c", "print('hello')"]) as exe:
        assert exe.wait(timeout=1) == 0


def test_executable_runner_streamreader():
    with Executable(sys.executable, ["-u", "-c", "print('hello')"]) as exe:
        assert exe.wait(1) == 0
        for line in exe.stdout:
            assert b"hello" in line
            break


def test_executable_pid():
    with Executable(sys.executable, ["-u", "-c", "import time; time.sleep(0.1)"]) as runner:
        assert runner.pid is not None
        runner.wait(timeout=1)
