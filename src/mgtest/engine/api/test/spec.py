import logging
from abc import ABC, abstractmethod

from mgtest.internal.spec_base import SpecBase

logger = logging.getLogger(__name__)


class TestSpec(SpecBase, ABC):
    """The definition of a single test. You should derive from this class to make your own tests"""

    @abstractmethod
    def create_instance(self) -> "TestInstance":
        """Create an instance of the test."""
        raise NotImplementedError
