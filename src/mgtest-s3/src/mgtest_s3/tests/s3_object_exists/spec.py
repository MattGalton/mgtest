from mgtest.api import TestSpec
from pydantic import BaseModel, Field

from mgtest_s3.tests.s3_object_exists.instance import S3ObjectExistsInstance


class S3ObjectExists(TestSpec):
    """Assert that an S3 bucket contains an object and report its metadata."""

    bucket: str = Field(description="S3 bucket containing the object.")
    key: str = Field(description="Object key that must exist.")
    region: str = Field(default="us-east-1", description="AWS region for the S3 client.")
    endpoint_url: str | None = Field(
        default=None, description="Optional S3-compatible endpoint URL."
    )

    class Output(BaseModel):
        exists: bool = Field(default=False, description="Whether the object exists.")
        etag: str = Field(default="", description="Object ETag returned by S3.")
        size: int = Field(default=0, description="Object size in bytes.")

    def create_instance(self) -> S3ObjectExistsInstance:
        return S3ObjectExistsInstance(self)
