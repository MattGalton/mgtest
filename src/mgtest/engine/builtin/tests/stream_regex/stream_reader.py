from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from typing import IO


class StreamReader(Iterator[bytes]):
    """Thread-safe, ordered, incremental reader for a binary stream.

    Reads are destructive: bytes returned by ``read`` or ``readline`` are removed
    from the shared buffer. Iteration blocks for complete lines until EOF.
    """

    def __init__(
        self,
        stream: IO[bytes],
        chunk_size: int = 4096,
        *,
        max_buffer_size: int = 1024 * 1024,
        close_stream: bool = False,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if max_buffer_size < chunk_size:
            raise ValueError("max_buffer_size must be at least chunk_size")
        self._stream = stream
        self._chunk_size = chunk_size
        self._max_buffer_size = max_buffer_size
        self._close_stream = close_stream
        self._buffer = bytearray()
        self._condition = threading.Condition()
        self._eof = False
        self._closed = False
        self._error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._read_loop, daemon=True, name="mgtest-stream-reader"
        )
        self._thread.start()

    def read(self) -> bytes:
        """Return and consume all bytes currently available without blocking."""
        with self._condition:
            self._raise_if_failed()
            data = bytes(self._buffer)
            self._buffer.clear()
            self._condition.notify_all()
            return data

    read_available = read

    def readline(self, timeout: float | None = 0.0) -> bytes | None:
        """Consume one line, waiting up to ``timeout`` seconds.

        ``timeout=0`` is non-blocking. ``None`` waits until a line, EOF, closure,
        or a reader error occurs.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while True:
                newline = self._buffer.find(b"\n")
                if newline >= 0:
                    return self._consume(newline + 1)
                if self._eof or self._closed:
                    if self._buffer:
                        return self._consume(len(self._buffer))
                    self._raise_if_failed()
                    return None
                self._raise_if_failed()
                if timeout == 0:
                    return None
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return None
                self._condition.wait(remaining)

    @property
    def eof(self) -> bool:
        """Whether the producer stream has reached EOF."""
        with self._condition:
            return self._eof

    @property
    def drained(self) -> bool:
        """Whether EOF was reached and all buffered bytes were consumed."""
        with self._condition:
            return self._eof and not self._buffer

    def close(self, timeout: float = 1.0) -> None:
        with self._condition:
            if self._closed:
                return
            self._closed = True
            self._condition.notify_all()
        if self._close_stream:
            self._stream.close()
        if self._thread is not threading.current_thread():
            self._thread.join(timeout)

    def __enter__(self) -> StreamReader:
        return self

    def __exit__(self, *_exc_info) -> None:
        self.close()

    def __iter__(self) -> StreamReader:
        return self

    def __next__(self) -> bytes:
        line = self.readline(timeout=None)
        if line is None:
            raise StopIteration
        return line

    def _consume(self, size: int) -> bytes:
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        self._condition.notify_all()
        return data

    def _raise_if_failed(self) -> None:
        if self._error is not None:
            raise RuntimeError("Background stream read failed") from self._error

    def _read_loop(self) -> None:
        try:
            while True:
                with self._condition:
                    while not self._closed and len(self._buffer) >= self._max_buffer_size:
                        self._condition.wait()
                    if self._closed:
                        return
                chunk = self._stream.read(self._chunk_size)
                if not chunk:
                    with self._condition:
                        self._eof = True
                        self._condition.notify_all()
                    return
                with self._condition:
                    self._buffer.extend(chunk)
                    self._condition.notify_all()
        except BaseException as error:
            with self._condition:
                if not self._closed:
                    self._error = error
                self._eof = True
                self._condition.notify_all()
