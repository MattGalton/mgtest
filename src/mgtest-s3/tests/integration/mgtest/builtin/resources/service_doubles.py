from io import BytesIO
from types import SimpleNamespace

from botocore.exceptions import ClientError
from mgtest_s3.resources.s3_bucket import instance as bucket_instance
from mgtest_s3.resources.s3_object import instance as object_instance
from mgtest_s3.tests.s3_object_exists import instance as exists_instance
from mgtest_s3.tests.s3_object_matches import instance as matches_instance


class S3Client:
    buckets = set()
    objects = {}

    def head_bucket(self, *, Bucket):
        if Bucket not in self.buckets:
            raise ClientError({"Error": {"Code": "404"}}, "HeadBucket")

    def create_bucket(self, *, Bucket, **_):
        self.buckets.add(Bucket)

    def delete_bucket(self, *, Bucket):
        self.buckets.remove(Bucket)

    def head_object(self, *, Bucket, Key):
        try:
            value = self.objects[Bucket, Key]
        except KeyError as error:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject") from error
        return {"ETag": '"fixture-etag"', "ContentLength": len(value)}

    def put_object(self, *, Bucket, Key, Body, **_):
        self.objects[Bucket, Key] = Body
        return {"ETag": '"fixture-etag"'}

    def get_object(self, *, Bucket, Key):
        return {"Body": BytesIO(self.objects[Bucket, Key].encode())}

    def delete_object(self, *, Bucket, Key):
        del self.objects[Bucket, Key]


client = S3Client()
s3 = SimpleNamespace(client=lambda *_args, **_kwargs: client)
for module in (bucket_instance, object_instance, exists_instance, matches_instance):
    module.boto3 = s3
