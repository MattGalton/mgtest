import logging

import boto3
from mgtest.api import TestInstance

logger = logging.getLogger(__name__)


class S3ObjectExistsInstance(TestInstance):
    def run(self, resources):
        logger.debug("Checking for S3 object %s/%s", self.definition.bucket, self.definition.key)
        client = boto3.client(
            "s3", region_name=self.definition.region, endpoint_url=self.definition.endpoint_url
        )
        result = client.head_object(Bucket=self.definition.bucket, Key=self.definition.key)
        self.outputs.exists = True
        self.outputs.etag = result.get("ETag", "").strip('"')
        self.outputs.size = result.get("ContentLength", 0)
