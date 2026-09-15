from mgtest.engine.builtin.resources.executable.spec import ExecutableDefinition
from mgtest.engine.builtin.tests.file_exists.spec import FileExistsSpec
from mgtest.engine.builtin.tests.stream_regex.spec import StreamRegexTestDefinition
from mgtest.engine.plugin.plugin_registries import PluginCatalog


def register_builtins(catalog: PluginCatalog) -> None:
    catalog.resources.register(ExecutableDefinition.TYPE, ExecutableDefinition)
    catalog.tests.register(FileExistsSpec.TYPE, FileExistsSpec)
    catalog.tests.register(StreamRegexTestDefinition.TYPE, StreamRegexTestDefinition)
