from mgtest.api import TestSpec
from pydantic import BaseModel, Field

from mgtest_s3.tests.s3_object_matches.instance import S3ObjectMatchesInstance


class S3ObjectMatches(TestSpec):
    """Read an S3 object and assert that its text equals or contains a value."""

    bucket: str = Field(description="S3 bucket containing the object.")
    key: str = Field(description="Object key whose text is checked.")
    contains: str | None = Field(default=None, description="Text that must occur in the object.")
    equals: str | None = Field(default=None, description="Exact text required for the object.")
    region: str = Field(default="us-east-1", description="AWS region for the S3 client.")
    endpoint_url: str | None = Field(default=None, description="Optional S3-compatible endpoint URL.")

    class Output(BaseModel):
        content: str = Field(default="", description="Text content read from the object.")

    def create_instance(self) -> S3ObjectMatchesInstance:
        return S3ObjectMatchesInstance(self)
