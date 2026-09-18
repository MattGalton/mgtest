import logging
import tarfile
import zipfile

from mgtest.api.test import TestInstance
from mgtest.engine.builtin.retry import retry

logger = logging.getLogger(__name__)


class ArchiveContainsInstance(TestInstance):
    def run(self, resources):
        path = self.definition.path
        logger.debug("Listing archive %s", path)
        check = self._entries_and_assert
        entries = (
            retry(check, timeout=self.definition.timeout, interval=self.definition.interval)
            if self.definition.timeout is not None
            else check()
        )
        self.outputs.entries = entries

    def _entries_and_assert(self):
        path = self.definition.path
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                entries = archive.namelist()
        elif tarfile.is_tarfile(path):
            with tarfile.open(path) as archive:
                entries = archive.getnames()
        else:
            raise ValueError(f"Unsupported archive: {path}")
        missing = sorted(set(self.definition.contains) - set(entries))
        assert not missing, f"Archive is missing: {', '.join(missing)}"
        return entries
