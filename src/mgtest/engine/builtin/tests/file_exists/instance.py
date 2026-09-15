from mgtest.engine.api.test.instance import TestInstance


class FileExistsInstance(TestInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._path = definition.path
        self.exists = False

    def run(self, resources):
        import os

        self.exists = os.path.exists(self._path)
        # Perhaps set outputs
        self.outputs.exists = self.exists

    def setup(self):
        pass

    def teardown(self):
        pass

    def value(self):
        return self.exists
