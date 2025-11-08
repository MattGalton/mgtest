import logging
from dataclasses import dataclass, field

from mgtest.engine.project.model import ProjectError, SourceLocation

logger = logging.getLogger(__name__)


@dataclass
class DependencyGraph:
    """Edges point from a dependent to its prerequisites."""

    dependencies: dict[str, set[str]] = field(default_factory=dict)
    reverse_dependencies: dict[str, set[str]] = field(default_factory=dict)
    locations: dict[tuple[str, str], list[SourceLocation]] = field(default_factory=dict)

    def add_node(self, identity):
        self.dependencies.setdefault(identity, set())
        self.reverse_dependencies.setdefault(identity, set())

    def add_edge(self, dependent, prerequisite, source):
        self.add_node(dependent)
        self.add_node(prerequisite)
        self.dependencies[dependent].add(prerequisite)
        self.reverse_dependencies[prerequisite].add(dependent)
        self.locations.setdefault((dependent, prerequisite), []).append(source)
        logger.debug("Added dependency %s -> %s", dependent, prerequisite)

    def topological_order(self):
        result, done, active = [], set(), []

        def visit(node):
            if node in done:
                return
            if node in active:
                cycle = active[active.index(node) :] + [node]
                source = self.locations[(active[-1], node)][0]
                raise ProjectError("Dependency cycle: " + " -> ".join(cycle), source)
            active.append(node)
            for dependency in sorted(self.dependencies[node]):
                visit(dependency)
            active.pop()
            done.add(node)
            result.append(node)

        for node in self.dependencies:
            visit(node)
        order = tuple(result)
        logger.info("Computed dependency order for %d definitions", len(order))
        return order
