from mgtest.engine.api.resource.instance import ResourceInstance
from mgtest.engine.builtin.resources.executable.executable import Executable


class ExecutableInstance(ResourceInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._path = definition.path
        self._args = definition.args

    def setup(self):
        self._exe = Executable(self._path, self._args)
        self._exe.spawn()
        self.outputs.exe = self._exe

    def teardown(self):
        if hasattr(self, "_exe"):
            self._exe.close()

    def value(self):
        return self._exe
