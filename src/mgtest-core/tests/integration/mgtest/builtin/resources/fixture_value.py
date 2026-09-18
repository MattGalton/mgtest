from mgtest.api.resource import ResourceInstance, ResourceSpec
from pydantic import BaseModel


class FixtureValueInstance(ResourceInstance):
    def setup(self):
        self.outputs.number = self.definition.number

    def teardown(self):
        pass


class FixtureValue(ResourceSpec):
    number: int

    class Output(BaseModel):
        number: int = 0

    def create_instance(self):
        return FixtureValueInstance(self)
