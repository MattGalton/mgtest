from mgtest.api.test import TestInstance, TestSpec


class FixtureStateInstance(TestInstance):
    def run(self, resources):
        resource = resources.required(self.definition.resource)
        assert resource.state == self.definition.expected_state
        if self.definition.set_state is not None:
            resource.state = self.definition.set_state


class FixtureState(TestSpec):
    resource: str
    expected_state: str
    set_state: str | None = None

    def validate_resources(self, resources):
        if self.resource not in resources:
            raise ValueError(f"Unknown resource '{self.resource}'")

    def create_instance(self):
        return FixtureStateInstance(self)
