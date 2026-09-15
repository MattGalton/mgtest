from mgtest.engine.api.test.instance import TestInstance


class StreamRegexTestInstance(TestInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self.resource = definition.resource
        self.pattern = definition.pattern

    def run(self, resources):
        import re

        resource = resources.required(self.resource)
        stream = resource.stdout

        regex = re.compile(self.pattern.encode())

        for line in stream:
            if regex.search(line):
                self.outputs.found = True
                return
        self.outputs.found = False
        raise AssertionError(f"Pattern not found: {self.pattern}")
