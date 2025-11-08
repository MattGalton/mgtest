import logging

from mgtest.api.test import TestInstance

logger = logging.getLogger(__name__)


class StreamRegexTestInstance(TestInstance):
    def run(self, resources):
        spec = self.definition
        logger.debug("Waiting for a pattern on %s.%s", spec.resource, spec.stream)
        resource = resources.required(spec.resource)
        stream = getattr(resource, spec.stream)
        try:
            self.outputs.found = stream.wait_for_pattern(spec.pattern.encode(), spec.timeout)
        except TimeoutError as error:
            raise AssertionError(
                f"Test '{spec.name}': timed out after {spec.timeout}s waiting for "
                f"{spec.pattern!r} on {spec.resource}.{spec.stream}"
            ) from error
        if not self.outputs.found:
            raise AssertionError(
                f"Test '{spec.name}': pattern {spec.pattern!r} not found on "
                f"{spec.resource}.{spec.stream} before EOF"
            )
