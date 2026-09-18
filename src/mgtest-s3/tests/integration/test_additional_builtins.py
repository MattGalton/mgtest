from __future__ import annotations

from botocore.exceptions import ClientError
from mgtest.engine import Engine
from mgtest.engine.plugin import PluginImporter
from mgtest_s3.resources.s3_object.spec import S3Object
from mgtest_s3.tests.s3_object_exists.spec import S3ObjectExists
from mgtest_s3.tests.s3_object_matches.spec import S3ObjectMatches


def _engine():
    importer = PluginImporter()
    importer.load()
    return Engine(importer.catalog)


def test_plugin_importer_registers_s3_builtins():
    catalog = _engine().catalog
    assert {"S3Bucket", "S3Object"} <= set(catalog.resources.keys())
    assert {"S3ObjectExists", "S3ObjectMatches"} <= set(catalog.tests.keys())


def test_s3_object_resource_and_checks_share_an_s3_client(monkeypatch):
    from mgtest_s3.resources.s3_object import instance as object_instance
    from mgtest_s3.tests.s3_object_exists import instance as exists_instance
    from mgtest_s3.tests.s3_object_matches import instance as matches_instance

    objects = {}

    class Body:
        def __init__(self, value):
            self.value = value

        def read(self):
            return self.value.encode()

    class Client:
        def head_object(self, **arguments):
            if (arguments["Bucket"], arguments["Key"]) not in objects:
                raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
            value = objects[(arguments["Bucket"], arguments["Key"])]
            return {"ETag": '"etag-1"', "ContentLength": len(value)}

        def put_object(self, **arguments):
            objects[(arguments["Bucket"], arguments["Key"])] = arguments["Body"]
            return {"ETag": '"etag-1"'}

        def get_object(self, **arguments):
            return {"Body": Body(objects[(arguments["Bucket"], arguments["Key"])])}

        def delete_object(self, **arguments):
            del objects[(arguments["Bucket"], arguments["Key"])]

    client = Client()
    for module in (object_instance, exists_instance, matches_instance):
        monkeypatch.setattr(module.boto3, "client", lambda *_args, **_kwargs: client)

    resource = S3Object(
        type="S3Object", name="fixture", bucket="test-bucket", key="status.txt", body="ready"
    ).create_instance()
    resource.setup()
    exists = S3ObjectExists(
        type="S3ObjectExists", name="exists", bucket="test-bucket", key="status.txt"
    ).create_instance()
    matches = S3ObjectMatches(
        type="S3ObjectMatches",
        name="matches",
        bucket="test-bucket",
        key="status.txt",
        equals="ready",
    ).create_instance()

    exists.run({})
    matches.run({})

    assert resource.outputs.etag == "etag-1"
    assert exists.outputs.size == 5
    assert matches.outputs.content == "ready"
    resource.teardown()
    assert objects == {}
