import io
import os
import threading
import time

from mgtest.engine.builtin.tests.stream_regex.stream_reader import StreamReader


def _wait_for_reader(reader, timeout=0.2, interval=0.01):
    """Wait until the StreamReader reaches EOF or timeout occurs."""
    elapsed = 0.0
    while not reader.eof and elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
    if not reader.eof:
        raise TimeoutError("StreamReader did not reach EOF within timeout")


def test_read_incremental():
    stream = io.BytesIO(b"hello\nworld\n")
    reader = StreamReader(stream)

    _wait_for_reader(reader)

    assert reader.read() == b"hello\nworld\n"
    assert reader.eof


def test_readline_multiple():
    stream = io.BytesIO(b"line1\nline2\nline3")
    reader = StreamReader(stream)
    _wait_for_reader(reader)

    lines = []
    while True:
        line = reader.readline()
        if line is None:
            break
        lines.append(line)

    assert lines == [b"line1\n", b"line2\n", b"line3"]


def test_empty_stream():
    stream = io.BytesIO(b"")
    reader = StreamReader(stream)
    _wait_for_reader(reader)

    assert reader.read() == b""
    assert reader.eof
    assert reader.readline() is None


def test_partial_line():
    stream = io.BytesIO(b"partial")
    reader = StreamReader(stream)
    _wait_for_reader(reader)

    assert reader.readline() == b"partial"
    assert reader.eof
    assert reader.readline() is None


def test_preserves_order_across_chunks():
    reader = StreamReader(io.BytesIO(b"one\ntwo\nthree\n"), chunk_size=4)
    _wait_for_reader(reader)
    assert list(reader) == [b"one\n", b"two\n", b"three\n"]
    assert reader.drained


def test_real_pipe_delivers_a_split_line_incrementally():
    read_fd, write_fd = os.pipe()
    read_stream = os.fdopen(read_fd, "rb", buffering=0)
    write_stream = os.fdopen(write_fd, "wb", buffering=0)
    reader = StreamReader(read_stream, chunk_size=2, close_stream=True)

    def write_chunks():
        write_stream.write(b"hel")
        time.sleep(0.02)
        write_stream.write(b"lo\n")
        write_stream.close()

    writer = threading.Thread(target=write_chunks)
    writer.start()
    assert reader.readline(timeout=1) == b"hello\n"
    writer.join()
    _wait_for_reader(reader, timeout=1)
    reader.close()


def test_readline_timeout():
    read_fd, write_fd = os.pipe()
    reader = StreamReader(os.fdopen(read_fd, "rb", buffering=0), close_stream=True)
    try:
        assert reader.readline(timeout=0.01) is None
    finally:
        os.close(write_fd)
        reader.close()


def test_background_error_is_reported():
    class BrokenStream:
        def read(self, _size):
            raise OSError("broken")

    reader = StreamReader(BrokenStream())
    _wait_for_reader(reader)
    import pytest

    with pytest.raises(RuntimeError, match="Background stream read failed"):
        reader.read()
