from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from mgtest.api.resource import ResourceScope
from mgtest.engine.project.graph import DependencyGraph
from mgtest.engine.project.model import Definition, ProjectError, ProjectModel, SourceLocation
from mgtest.engine.project.references import (
    Interpolation,
    OutputReference,
    Reference,
    ReferenceBinding,
    get_path,
    output_references,
    parse,
    resolve,
)
from mgtest.engine.project.validation import authored_schema, output_annotation, validate_fields

logger = logging.getLogger(__name__)


@dataclass
class CompiledDefinition:
    definition: Definition
    spec_class: type
    data: dict[str, Any]
    spec: Any = None

    @property
    def name(self):
        return self.definition.name

    def materialize(self, lookup):
        try:
            # Validate even cached literals again: a runtime instance must not mutate the plan.
            spec = self.spec_class.model_validate(resolve(self.data, lookup))
            if self.definition.kind == "tests":
                spec.source_path = self.definition.source.path
            return spec
        except (ValueError, TypeError) as error:
            raise ProjectError(str(error), self.definition.source) from error


@dataclass
class CompiledResource(CompiledDefinition):
    """A planned resource with its lifecycle configuration."""

    @property
    def scope(self):
        return self.data.get("scope", ResourceScope.SUITE)

    @property
    def auto_start(self):
        return self.data.get("auto_start", False)


@dataclass
class CompiledTest(CompiledDefinition):
    """A planned check with its expected execution outcome."""

    @property
    def expected_outcome(self):
        return self.data.get("expected_outcome", "passed")


@dataclass
class CompiledProject:
    model: ProjectModel
    definitions: dict[str, CompiledDefinition]
    graph: DependencyGraph
    definition_order: tuple[str, ...]
    test_order: tuple[str, ...]
    schemas: dict[str, dict] = field(default_factory=dict)
    references: tuple[ReferenceBinding, ...] = ()

    @property
    def resources(self) -> dict[str, CompiledResource]:
        """Return the resource nodes keyed by their stable identities."""
        return {
            identity: node
            for identity, node in self.definitions.items()
            if isinstance(node, CompiledResource)
        }

    @property
    def tests(self) -> dict[str, CompiledTest]:
        """Return the check nodes keyed by their stable identities."""
        return {
            identity: node
            for identity, node in self.definitions.items()
            if isinstance(node, CompiledTest)
        }

    def resource(self, identity: str) -> CompiledResource:
        """Return one resource node or reject a check identity."""
        node = self.definitions[identity]
        if not isinstance(node, CompiledResource):
            raise ValueError(f"Expected a resource identity, got {identity}")
        return node

    def test(self, identity: str) -> CompiledTest:
        """Return one check node or reject a resource identity."""
        node = self.definitions[identity]
        if not isinstance(node, CompiledTest):
            raise ValueError(f"Expected a test identity, got {identity}")
        return node

    def prerequisites(self, identity: str) -> tuple[str, ...]:
        """Return direct prerequisites in the compiler's deterministic order."""
        required = self.graph.dependencies[identity]
        return tuple(item for item in self.definition_order if item in required)

    def resource_dependencies(self, identity: str) -> tuple[str, ...]:
        """Return direct resource prerequisites in deterministic order."""
        return tuple(
            dependency
            for dependency in self.prerequisites(identity)
            if isinstance(self.definitions[dependency], CompiledResource)
        )

    def test_dependencies(self, identity: str) -> tuple[str, ...]:
        """Return direct check prerequisites in deterministic order."""
        return tuple(
            dependency
            for dependency in self.prerequisites(identity)
            if isinstance(self.definitions[dependency], CompiledTest)
        )

    def requirements_for(self, test_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Return resource closure and prerequisite checks for one selected check."""
        self.test(test_id)
        resources: set[str] = set()
        prerequisite_tests: set[str] = set()

        def visit(identity: str) -> None:
            for dependency in self.prerequisites(identity):
                node = self.definitions[dependency]
                if isinstance(node, CompiledResource):
                    if dependency not in resources:
                        resources.add(dependency)
                        visit(dependency)
                elif dependency not in prerequisite_tests:
                    prerequisite_tests.add(dependency)
                    visit(dependency)

        visit(test_id)
        suite = self.test(test_id).definition.suite
        for identity in self.model.visible(suite, "resources").values():
            if self.resource(identity).auto_start:
                resources.add(identity)
                visit(identity)
        return (
            tuple(item for item in self.definition_order if item in resources),
            tuple(item for item in self.definition_order if item in prerequisite_tests),
        )


class ProjectCompiler:
    def __init__(self, catalog):
        self.catalog = catalog

    def compile(self, model: ProjectModel) -> CompiledProject:
        logger.info("Compiling project %s", model.root)
        self.model = model
        self.classes = {}
        self.cache = {}
        self.active = []
        self.graph = DependencyGraph()
        self.references = []
        self._register_node_types()
        self._resolve_variables()
        definitions = self._compile_nodes()
        order = self._validate_lifecycle(definitions)
        return self._build_project(definitions, order)

    def _register_node_types(self) -> None:
        """Resolve every authored type name and initialise the dependency graph."""
        for identity, definition in self.model.definitions.items():
            type_name = definition.data.get("type")
            if not isinstance(type_name, str) or "${" in type_name:
                raise ProjectError(
                    "Every definition requires a literal string 'type'", definition.source
                )
            registry = getattr(self.catalog, definition.kind)
            try:
                self.classes[identity] = registry[type_name]
            except KeyError as error:
                raise ProjectError(str(error), definition.location(("type",))) from error
            self.graph.add_node(identity)

    def _resolve_variables(self) -> None:
        """Resolve variable expressions before compiling authored definitions."""
        for suite in self.model.suites.values():
            for name in suite.variables:
                self.variable(
                    suite.id,
                    (name,),
                    suite.variable_locations.get((name,))
                    or SourceLocation(suite.path / "vars.yaml"),
                )

    def _compile_nodes(self) -> dict[str, CompiledDefinition]:
        """Resolve configuration, validate literals, and add dependency edges."""
        definitions = {}
        for identity, definition in self.model.definitions.items():
            data = self.value(identity, ())
            cls = self.classes[identity]
            self._validate_planning_fields(definition, data)
            compiled_type = CompiledResource if definition.kind == "resources" else CompiledTest
            compiled = compiled_type(definition, cls, data)
            if any(output_references(data)):
                validate_fields(data, cls, definition.location)
            else:
                try:
                    compiled.spec = cls.model_validate(data)
                    if isinstance(compiled, CompiledTest):
                        compiled.spec.source_path = definition.source.path
                except ValueError as error:
                    error.add_note(str(definition.source))
                    raise
            definitions[identity] = compiled
            self._add_node_dependencies(compiled)
        return definitions

    def _validate_planning_fields(self, definition: Definition, data: dict) -> None:
        """Reject output-dependent identity and lifecycle configuration."""
        for field_name in ("name", "type", "scope", "auto_start", "expected_outcome"):
            if any(output_references(data.get(field_name))):
                raise ProjectError(
                    f"'{field_name}' must resolve during planning",
                    definition.location((field_name,)),
                )

    def _add_node_dependencies(self, node: CompiledDefinition) -> None:
        """Add output-reference and explicit dependency edges for one node."""
        for reference in output_references(node.data):
            self.graph.add_edge(node.definition.id, reference.target, reference.source)
        for dependency in node.definition.depends_on:
            target = self.lookup(
                node.definition.suite,
                dependency,
                node.definition.location(("depends_on",)),
            )
            self.graph.add_edge(
                node.definition.id,
                target,
                node.definition.location(("depends_on",)),
            )

    def _validate_lifecycle(self, definitions: dict[str, CompiledDefinition]) -> tuple[str, ...]:
        """Validate resource scope rules and per-check visible resources."""
        logger.info("Computing dependency graph for %d definitions", len(definitions))
        order = self.graph.topological_order()
        for identity, dependencies in self.graph.dependencies.items():
            node = definitions[identity]
            for dependency in dependencies:
                required = definitions[dependency]
                if isinstance(node, CompiledResource):
                    if isinstance(required, CompiledTest):
                        raise ProjectError(
                            "Resources cannot depend on test results", node.definition.source
                        )
                    if node.scope == ResourceScope.SUITE and required.scope == ResourceScope.TEST:
                        raise ProjectError(
                            "Suite resource cannot depend on a Test-scoped resource",
                            node.definition.source,
                        )
            if isinstance(node, CompiledTest) and node.spec is not None:
                visible = {
                    name: definitions[target].spec or definitions[target]
                    for name, target in self.model.visible(
                        node.definition.suite, "resources"
                    ).items()
                }
                node.spec.validate_resources(visible)
        return order

    def _build_project(
        self, definitions: dict[str, CompiledDefinition], order: tuple[str, ...]
    ) -> CompiledProject:
        """Select checks and assemble the immutable compiled snapshot."""
        model = self.model
        suite_tests = model.tests_in_selection(model.selection)
        selected = tuple(
            identity
            for identity in order
            if isinstance(definitions[identity], CompiledTest)
            and identity in suite_tests
            and (model.selected_tests is None or identity in model.selected_tests)
        )
        if not selected:
            raise ValueError(f"No tests defined in {model.suites[model.selection].path}")
        schemas = {
            identity: {
                "input": authored_schema(cls),
                "output": (
                    cls.output_model().model_json_schema()
                    if cls.output_model()
                    else {"type": "object", "additionalProperties": True}
                ),
            }
            for identity, cls in self.classes.items()
        }
        compiled = CompiledProject(
            model, definitions, self.graph, order, selected, schemas, tuple(self.references)
        )
        logger.info(
            "Compiled %d definitions into %d selected checks", len(definitions), len(selected)
        )
        return compiled

    def lookup(self, suite, expression, source):
        parts = expression.split(".")
        if len(parts) != 2 or parts[0] not in ("resources", "tests"):
            raise ProjectError("Dependency must be 'resources.name' or 'tests.name'", source)
        visible = self.model.visible(suite, parts[0])
        if parts[1] not in visible:
            raise ProjectError(f"Unknown or invisible {expression}", source)
        return visible[parts[1]]

    def value(self, identity, path):
        key = (identity, path)
        if key in self.cache:
            return self.cache[key]
        definition = self.model.definitions[identity]
        source = definition.location(path)
        if key in self.active:
            chain = " -> ".join(
                f"{item[0]}:{'.'.join(map(str, item[1]))}" for item in [*self.active, key]
            )
            raise ProjectError(f"Configuration reference cycle: {chain}", source)
        self.active.append(key)
        try:
            raw = get_path(definition.data, path)
            if isinstance(raw, dict):
                result = {k: self.value(identity, (*path, k)) for k in raw}
            elif isinstance(raw, list):
                result = [self.value(identity, (*path, i)) for i in range(len(raw))]
            else:
                result = self.bind(parse(raw, source), definition.suite)
            self.cache[key] = result
            return result
        finally:
            self.active.pop()

    def bind(self, value, suite):
        if isinstance(value, Interpolation):
            parts = tuple(self.bind(part, suite) for part in value.parts)
            result = Interpolation(parts)
            return result if any(output_references(result)) else resolve(result, None)
        if not isinstance(value, Reference):
            return value
        expression = value.expression.removeprefix("mgtest:")
        parts = expression.split(".")
        if parts[0] not in ("resources", "tests"):
            path = parts[1:] if parts[0] == "vars" else parts
            if path:
                try:
                    owner = self.model.variable_owner(suite, path[0])
                    self.record(value, f"vars@{owner.id}", tuple(path), False)
                except KeyError:
                    pass
            return self.variable(suite, tuple(path), value.source)
        if len(parts) == 2:
            if parts[0] != "resources":
                raise ProjectError("Only resources can be referenced directly", value.source)
            target = self.lookup(suite, expression, value.source)
            self.record(value, target, (), True)
            owner, _ = self.active[-1]
            self.graph.add_edge(owner, target, value.source)
            return self.model.definitions[target].name
        if len(parts) < 3:
            raise ProjectError("References require a configuration or output field", value.source)
        target = self.lookup(suite, ".".join(parts[:2]), value.source)
        self.record(value, target, tuple(parts[2:]), parts[2] == "outputs")
        if parts[2] == "outputs":
            if len(parts) < 4:
                raise ProjectError("Specify an output field", value.source)
            output = self.classes[target].output_model()
            annotation = output_annotation(output, parts[3:], value.source) if output else Any
            return OutputReference(target, tuple(parts[3:]), annotation, value.source)
        try:
            # Numeric path components address list entries.
            path = tuple(int(part) if part.isdigit() else part for part in parts[2:])
            return self.value(target, path)
        except (KeyError, IndexError, AttributeError, TypeError) as error:
            raise ProjectError(
                f"Unknown configuration reference '{value.expression}'", value.source
            ) from error

    def record(self, reference, target, path, runtime):
        owner, owner_path = self.active[-1]
        self.references.append(
            ReferenceBinding(reference, owner, owner_path, target, path, runtime)
        )

    def variable(self, suite, path, source):
        if not path:
            raise ProjectError("Specify a variable name", source)
        try:
            owner = self.model.variable_owner(suite, path[0])
            key = (f"vars@{owner.id}", path)
            if key in self.active:
                raise ProjectError(
                    f"Configuration reference cycle involving vars.{'.'.join(path)}", source
                )
            if key in self.cache:
                return self.cache[key]
            self.active.append(key)
            try:
                raw = get_path(owner.variables, path)
                location = owner.variable_locations.get(path, source)

                def bind_value(item):
                    if isinstance(item, dict):
                        return {k: bind_value(v) for k, v in item.items()}
                    if isinstance(item, list):
                        return [bind_value(v) for v in item]
                    return self.bind(parse(item, location), owner.id)

                result = bind_value(raw)
                self.cache[key] = result
                return result
            finally:
                self.active.pop()
        except (KeyError, IndexError, AttributeError, TypeError) as error:
            raise ProjectError(f"Unknown variable vars.{'.'.join(path)}", source) from error
