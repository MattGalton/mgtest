from mgtest.api.resource import ResourceInstance, ResourceSpec
from pydantic import BaseModel


class ResettableFixtureInstance(ResourceInstance):
    """A test fixture whose state makes lifecycle mistakes visible."""

    active = False
    last_instance = None
    generations = 0

    def setup(self):
        assert not type(self).active, "previous resource instance was not torn down"
        assert self is not type(self).last_instance, "resource instance was reused"
        type(self).active = True
        type(self).last_instance = self
        type(self).generations += 1
        self.state = "fresh"
        self.outputs.generation = type(self).generations

    def teardown(self):
        self.state = "reset"
        type(self).active = False


class ResettableFixture(ResourceSpec):
    class Output(BaseModel):
        generation: int = 0

    def create_instance(self):
        return ResettableFixtureInstance(self)
