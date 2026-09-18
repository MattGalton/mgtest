from __future__ import annotations

import logging

import boto3
from botocore.exceptions import ClientError
from mgtest.api import ResourceInstance

logger = logging.getLogger(__name__)


class S3BucketInstance(ResourceInstance):
    """Create a bucket when absent and remove only buckets this instance created."""

    def __init__(self, definition):
        super().__init__(definition)
        self._client = None
        self._created = False

    def setup(self):
        logger.debug("Ensuring S3 bucket %s exists", self.definition.bucket)
        self._client = boto3.client(
            "s3",
            region_name=self.definition.region,
            endpoint_url=self.definition.endpoint_url,
        )
        try:
            self._client.head_bucket(Bucket=self.definition.bucket)
        except ClientError as error:
            if _error_code(error) not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            arguments = {"Bucket": self.definition.bucket}
            if self.definition.region != "us-east-1":
                arguments["CreateBucketConfiguration"] = {
                    "LocationConstraint": self.definition.region
                }
            self._client.create_bucket(**arguments)
            self._created = True
            logger.debug("Created S3 bucket %s", self.definition.bucket)
        self.outputs.bucket = self.definition.bucket
        self.outputs.uri = f"s3://{self.definition.bucket}"
        self.outputs.region = self.definition.region
        self.outputs.endpoint_url = self.definition.endpoint_url

    def teardown(self):
        if self._created and self.definition.delete_on_teardown and self._client is not None:
            logger.debug("Deleting S3 bucket %s", self.definition.bucket)
            self._client.delete_bucket(Bucket=self.definition.bucket)


def _error_code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))
