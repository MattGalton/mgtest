from abc import ABC, abstractmethod


class TestInstance(ABC):
    def __init__(self, definition):
        self.definition = definition
        self._inputs = None
        self._outputs = None

    @abstractmethod
    def run(self, resources): ...

    @property
    def inputs(self):
        if self._inputs is None:
            self._inputs = self.definition.Inputs()
        return self._inputs

    @property
    def outputs(self):
        if self._outputs is None:
            self._outputs = self.definition.Outputs()
        return self._outputs
