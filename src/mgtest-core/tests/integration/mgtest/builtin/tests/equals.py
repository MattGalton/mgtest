from mgtest.api.test import TestInstance, TestSpec
from pydantic import BaseModel


class EqualsInstance(TestInstance):
    def run(self, resources):
        assert self.definition.actual == self.definition.expected
        self.outputs.value = self.definition.actual


class Equals(TestSpec):
    actual: int
    expected: int

    class Output(BaseModel):
        value: int = 0

    def create_instance(self):
        return EqualsInstance(self)
