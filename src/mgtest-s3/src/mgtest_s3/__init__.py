"""Amazon S3 resources and checks for mgtest."""

from mgtest_s3.resources.s3_bucket.spec import S3Bucket
from mgtest_s3.resources.s3_object.spec import S3Object
from mgtest_s3.tests.s3_object_exists.spec import S3ObjectExists
from mgtest_s3.tests.s3_object_matches.spec import S3ObjectMatches

__all__ = ["S3Bucket", "S3Object", "S3ObjectExists", "S3ObjectMatches"]
