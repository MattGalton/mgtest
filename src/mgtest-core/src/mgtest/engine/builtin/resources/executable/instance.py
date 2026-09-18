import logging

from mgtest.api.resource import ResourceInstance
from mgtest.engine.builtin.resources.executable.executable import Executable


class ExecutableInstance(ResourceInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._path = definition.path
        self._args = definition.args

    def setup(self):
        logger.debug("Starting executable %s", self._path)
        self._exe = Executable(
            self._path, self._args, max_output_bytes=self.definition.max_output_bytes
        )
        self._exe.spawn()
        self.outputs.exe = self._exe

    def teardown(self):
        if hasattr(self, "_exe"):
            self._exe.close()

    def value(self):
        return self._exe


logger = logging.getLogger(__name__)
