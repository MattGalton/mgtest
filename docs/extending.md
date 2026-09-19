# Extend mgtest

When a built-in or integration does not describe your system, add a local extension
under `mgtest/builtin/resources` or `mgtest/builtin/tests`. Packages can use the same
public API to provide reusable integrations.

An extension has a Pydantic spec, which defines the YAML fields, and an instance that
performs the runtime work. Import the public contracts from `mgtest.api`.

```python
from mgtest.api import TestInstance, TestSpec


class IsEvenInstance(TestInstance):
    def run(self, resources):
        assert self.definition.value % 2 == 0


class IsEven(TestSpec):
    value: int

    def create_instance(self):
        return IsEvenInstance(self)
```

```yaml
type: IsEven
name: answer
value: 42
```

Resource extensions inherit from `ResourceSpec` and implement `setup()` and
`teardown()` on their `ResourceInstance`. They may expose a Pydantic `Output` model
when other YAML definitions need typed, reusable results.

```python
from mgtest.api import ResourceInstance, ResourceSpec
```

The public API is the supported extension boundary. Compiler, runner, and built-in
implementation modules are internals and may change as mgtest evolves.
