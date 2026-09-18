from botocore.exceptions import ClientError
from mgtest_s3.resources.s3_bucket import instance
from mgtest_s3.resources.s3_bucket.spec import S3Bucket


def test_s3_bucket_creates_missing_bucket_and_removes_it_on_teardown(monkeypatch):
    calls = []

    class Client:
        def head_bucket(self, **arguments):
            calls.append(("head_bucket", arguments))
            raise ClientError({"Error": {"Code": "404"}}, "HeadBucket")

        def create_bucket(self, **arguments):
            calls.append(("create_bucket", arguments))

        def delete_bucket(self, **arguments):
            calls.append(("delete_bucket", arguments))

    monkeypatch.setattr(instance.boto3, "client", lambda *_args, **_kwargs: Client())
    resource = S3Bucket(
        type="S3Bucket",
        name="uploads",
        bucket="mgtest-example-bucket",
        region="eu-west-2",
        endpoint_url="http://localhost:4566",
    ).create_instance()

    resource.setup()

    assert resource.outputs.bucket == "mgtest-example-bucket"
    assert resource.outputs.uri == "s3://mgtest-example-bucket"
    assert calls == [
        ("head_bucket", {"Bucket": "mgtest-example-bucket"}),
        (
            "create_bucket",
            {
                "Bucket": "mgtest-example-bucket",
                "CreateBucketConfiguration": {"LocationConstraint": "eu-west-2"},
            },
        ),
    ]
    resource.teardown()
    assert calls[-1] == ("delete_bucket", {"Bucket": "mgtest-example-bucket"})


def test_s3_bucket_adopts_an_existing_bucket_without_deleting_it(monkeypatch):
    calls = []

    class Client:
        def head_bucket(self, **arguments):
            calls.append(("head_bucket", arguments))

        def create_bucket(self, **arguments):
            calls.append(("create_bucket", arguments))

        def delete_bucket(self, **arguments):
            calls.append(("delete_bucket", arguments))

    monkeypatch.setattr(instance.boto3, "client", lambda *_args, **_kwargs: Client())
    resource = S3Bucket(type="S3Bucket", name="uploads", bucket="existing-bucket").create_instance()

    resource.setup()
    resource.teardown()

    assert calls == [("head_bucket", {"Bucket": "existing-bucket"})]
