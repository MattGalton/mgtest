from __future__ import annotations

import logging
import subprocess

from mgtest.engine.builtin.tests.stream_regex.stream_reader import StreamReader

logger = logging.getLogger(__name__)


class Executable:
    def __init__(
        self, path: str, args: list[str] | None = None, *, max_output_bytes: int = 1024 * 1024
    ):
        self.path = path
        self.args = list(args or ())
        self.max_output_bytes = max_output_bytes
        self._process: subprocess.Popen[bytes] | None = None
        self._stdout_reader: StreamReader | None = None
        self._stderr_reader: StreamReader | None = None

    def spawn(self) -> Executable:
        if self._process is not None:
            raise RuntimeError("Process already spawned")
        logger.debug("Spawning executable %s", self.path)
        self._process = subprocess.Popen(
            [self.path, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        assert self._process.stdout is not None and self._process.stderr is not None
        self._stdout_reader = StreamReader(
            self._process.stdout, close_stream=True, max_buffer_size=self.max_output_bytes
        )
        self._stderr_reader = StreamReader(
            self._process.stderr, close_stream=True, max_buffer_size=self.max_output_bytes
        )
        return self

    @property
    def stdout(self) -> StreamReader:
        self._validate()
        assert self._stdout_reader is not None
        return self._stdout_reader

    @property
    def stderr(self) -> StreamReader:
        self._validate()
        assert self._stderr_reader is not None
        return self._stderr_reader

    @property
    def pid(self) -> int:
        self._validate()
        assert self._process is not None
        return self._process.pid

    @property
    def returncode(self) -> int | None:
        self._validate()
        assert self._process is not None
        return self._process.poll()

    def kill(self) -> None:
        self._stop(force=True)

    def terminate(self) -> None:
        self._stop(force=False)

    def wait(self, timeout: float | None = None) -> int:
        self._validate()
        assert self._process is not None
        return self._process.wait(timeout=timeout)

    def close(self, timeout: float = 1.0) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            logger.debug("Stopping executable process %s", self._process.pid)
            self._process.terminate()
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=timeout)
        if self._process.stdin is not None:
            self._process.stdin.close()
        if self._stdout_reader is not None:
            self._stdout_reader.close(timeout)
        if self._stderr_reader is not None:
            self._stderr_reader.close(timeout)
        errors = []
        for reader in (self._stdout_reader, self._stderr_reader):
            if reader is not None:
                try:
                    reader.check_error()
                except Exception as error:
                    errors.append(error)
        if errors:
            raise ExceptionGroup("Executable output capture failed", errors)

    def __enter__(self) -> Executable:
        return self.spawn()

    def __exit__(self, *_exc_info) -> None:
        self.close()

    def _stop(self, *, force: bool) -> None:
        self._validate()
        assert self._process is not None
        if self._process.poll() is None:
            (self._process.kill if force else self._process.terminate)()

    def _validate(self) -> None:
        if self._process is None:
            raise RuntimeError("Process not spawned")
