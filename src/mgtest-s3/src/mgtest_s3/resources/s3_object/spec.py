from mgtest.api import ResourceSpec
from pydantic import BaseModel

from mgtest_s3.resources.s3_object.instance import S3ObjectInstance


class S3Object(ResourceSpec):
    """Upload an S3 object and optionally delete it during resource teardown."""

    bucket: str
    key: str
    body: str = ""
    content_type: str | None = None
    overwrite: bool = False
    region: str = "us-east-1"
    endpoint_url: str | None = None
    delete_on_teardown: bool = True

    class Output(BaseModel):
        bucket: str = ""
        key: str = ""
        uri: str = ""
        etag: str = ""

    def create_instance(self) -> S3ObjectInstance:
        return S3ObjectInstance(self)
