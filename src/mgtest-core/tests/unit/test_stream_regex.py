import sys
import time
from types import SimpleNamespace

import pytest
from mgtest.engine.builtin.resources.executable.executable import Executable
from mgtest.engine.builtin.tests.stream_regex.spec import StreamRegex


def test_live_process_times_out_and_is_cleaned():
    check = StreamRegex(
        type="StreamRegex",
        name="missing",
        resource="process",
        pattern="never",
        timeout=0.05,
    ).create_instance()
    started = time.monotonic()
    with Executable(sys.executable, ["-c", "import time; time.sleep(30)"]) as process:
        with pytest.raises(AssertionError, match="missing.*timed out"):
            check.run(SimpleNamespace(required=lambda name: process))
    assert process.returncode is not None
    assert time.monotonic() - started < 3


def test_stderr_selection():
    check = StreamRegex(
        type="StreamRegex",
        name="stderr",
        resource="process",
        pattern="ready",
        stream="stderr",
    ).create_instance()
    with Executable(
        sys.executable, ["-c", "import sys; print('ready', file=sys.stderr)"]
    ) as process:
        check.run(SimpleNamespace(required=lambda name: process))
        assert check.outputs.found


def test_unmatched_eof_is_a_failure():
    check = StreamRegex(
        type="StreamRegex",
        name="missing",
        resource="process",
        pattern="never",
    ).create_instance()
    with Executable(sys.executable, ["-c", "print('other')"]) as process:
        with pytest.raises(AssertionError, match="before EOF"):
            check.run(SimpleNamespace(required=lambda name: process))


def test_unread_stderr_overflow_does_not_block_process_and_fails_cleanup():
    process = Executable(
        sys.executable,
        ["-c", "import sys; sys.stderr.write('x' * 200000); sys.stderr.flush()"],
        max_output_bytes=4096,
    ).spawn()
    try:
        # This exceeds an OS pipe buffer: the producer must drain even after capture fails.
        assert process.wait(timeout=3) == 0
    finally:
        with pytest.raises(ExceptionGroup, match="output capture"):
            process.close()
