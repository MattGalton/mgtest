from pathlib import Path
from zipfile import ZipFile

from mgtest.api.resource import ResourceInstance, ResourceSpec
from pydantic import BaseModel


class ArchiveFixtureInstance(ResourceInstance):
    def setup(self):
        directory = Path(self.definition.directory)
        directory.mkdir(parents=True, exist_ok=True)
        text_path = directory / "message.txt"
        text_path.write_text(self.definition.message)
        archive_path = directory / "fixture.zip"
        with ZipFile(archive_path, "w") as archive:
            archive.write(text_path, "message.txt")
        self.outputs.text_path = text_path
        self.outputs.archive_path = archive_path

    def teardown(self):
        pass


class ArchiveFixture(ResourceSpec):
    directory: str
    message: str

    class Output(BaseModel):
        text_path: Path = Path()
        archive_path: Path = Path()

    def create_instance(self):
        return ArchiveFixtureInstance(self)
