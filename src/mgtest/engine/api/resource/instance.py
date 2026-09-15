from abc import ABC, abstractmethod


class ResourceInstance(ABC):
    def __init__(self, definition):
        self.definition = definition
        self._outputs = None

    @abstractmethod
    def setup(self): ...

    @abstractmethod
    def teardown(self): ...

    def value(self):
        return self

    @property
    def outputs(self):
        if self._outputs is None:
            self._outputs = self.definition.Outputs()
        return self._outputs
