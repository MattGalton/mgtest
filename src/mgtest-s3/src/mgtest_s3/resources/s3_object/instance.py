import logging

import boto3
from botocore.exceptions import ClientError
from mgtest.api import ResourceInstance

logger = logging.getLogger(__name__)


class S3ObjectInstance(ResourceInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._client = None
        self._created = False

    def setup(self):
        logger.debug("Writing S3 object %s/%s", self.definition.bucket, self.definition.key)
        self._client = boto3.client(
            "s3", region_name=self.definition.region, endpoint_url=self.definition.endpoint_url
        )
        self._created = self._is_missing()
        if not self._created and not self.definition.overwrite:
            raise ValueError(
                f"S3 object already exists: s3://{self.definition.bucket}/{self.definition.key}"
            )
        arguments = {
            "Bucket": self.definition.bucket,
            "Key": self.definition.key,
            "Body": self.definition.body,
        }
        if self.definition.content_type:
            arguments["ContentType"] = self.definition.content_type
        result = self._client.put_object(**arguments)
        self.outputs.bucket = self.definition.bucket
        self.outputs.key = self.definition.key
        self.outputs.uri = f"s3://{self.definition.bucket}/{self.definition.key}"
        self.outputs.etag = result.get("ETag", "").strip('"')

    def teardown(self):
        if self._created and self.definition.delete_on_teardown and self._client is not None:
            logger.debug("Deleting S3 object %s/%s", self.definition.bucket, self.definition.key)
            self._client.delete_object(Bucket=self.definition.bucket, Key=self.definition.key)

    def _is_missing(self) -> bool:
        try:
            self._client.head_object(Bucket=self.definition.bucket, Key=self.definition.key)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return True
            raise
        return False
