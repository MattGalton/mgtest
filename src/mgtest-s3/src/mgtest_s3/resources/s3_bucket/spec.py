from mgtest.api import ResourceSpec
from pydantic import BaseModel, Field

from mgtest_s3.resources.s3_bucket.instance import S3BucketInstance


class S3Bucket(ResourceSpec):
    """An S3 bucket created for a test run and optionally removed during teardown."""

    bucket: str = Field(min_length=3, max_length=63)
    region: str = "us-east-1"
    endpoint_url: str | None = None
    delete_on_teardown: bool = True

    class Output(BaseModel):
        bucket: str = ""
        uri: str = ""
        region: str = ""
        endpoint_url: str | None = None

    def create_instance(self) -> S3BucketInstance:
        return S3BucketInstance(self)
