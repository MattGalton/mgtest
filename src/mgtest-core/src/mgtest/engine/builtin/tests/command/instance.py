from __future__ import annotations

import logging
import os
import subprocess
import sys

from mgtest.api.test import TestInstance

logger = logging.getLogger(__name__)


class CommandInstance(TestInstance):
    def run(self, resources):
        command = self.definition.shell_command
        shell = command is not None
        logger.debug("Executing %s command", "shell" if shell else "Python")
        if self.definition.python_command is not None:
            command = [sys.executable, "-c", self.definition.python_command]
        result = subprocess.run(
            command,
            shell=shell,
            text=True,
            capture_output=True,
            cwd=self.definition.cwd,
            env=os.environ | self.definition.environment,
            timeout=self.definition.timeout,
        )
        self.outputs.exit_code = result.returncode
        self.outputs.stdout = result.stdout
        self.outputs.stderr = result.stderr
        assert result.returncode == self.definition.expected_exit_code, result.stderr
        if self.definition.stdout_contains is not None:
            assert self.definition.stdout_contains in result.stdout, result.stdout
        if self.definition.stderr_contains is not None:
            assert self.definition.stderr_contains in result.stderr, result.stderr
