import logging

import boto3
from mgtest.api import TestInstance

logger = logging.getLogger(__name__)


class S3ObjectMatchesInstance(TestInstance):
    def run(self, resources):
        logger.debug("Reading S3 object %s/%s", self.definition.bucket, self.definition.key)
        client = boto3.client(
            "s3", region_name=self.definition.region, endpoint_url=self.definition.endpoint_url
        )
        result = client.get_object(Bucket=self.definition.bucket, Key=self.definition.key)
        content = result["Body"].read().decode()
        self.outputs.content = content
        if self.definition.contains is not None:
            assert self.definition.contains in content, content
        if self.definition.equals is not None:
            assert self.definition.equals == content, content
