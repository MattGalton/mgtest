import logging

from jsonschema import validate

from mgtest.api.test import TestInstance

logger = logging.getLogger(__name__)


class JsonSchemaInstance(TestInstance):
    def run(self, resources):
        logger.debug("Validating a document against its JSON schema")
        validate(self.definition.document, self.definition.json_schema)
        self.outputs.document = self.definition.document
