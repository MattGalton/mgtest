import logging
import shutil
import tempfile

from mgtest.api.resource import ResourceInstance

logger = logging.getLogger(__name__)


class TemporaryDirectoryInstance(ResourceInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._path = None

    def setup(self):
        self.prepare()

    def prepare(self):
        if self._path is not None:
            return
        self._path = tempfile.mkdtemp(prefix=self.definition.prefix, dir=self.definition.parent)
        logger.debug("Created temporary directory %s", self._path)
        self.outputs.path = self._path

    def teardown(self):
        if self._path is not None and self.definition.delete_on_teardown:
            logger.debug("Removing temporary directory %s", self._path)
            shutil.rmtree(self._path, ignore_errors=True)
