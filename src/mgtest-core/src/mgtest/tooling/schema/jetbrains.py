import logging
import shutil
from pathlib import Path
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from pydantic import BaseModel

from mgtest.project.layout import RESOURCE_GLOBS, TEST_GLOBS

logger = logging.getLogger(__name__)


class _SchemaMapping(BaseModel):
    file: str
    pattern: str


class _YAMLSchemaMappings(BaseModel):
    mapping: list[_SchemaMapping] = []


class _ApplicationComponent(BaseModel):
    name: str
    yaml_schema_mappings: _YAMLSchemaMappings


class _Application(BaseModel):
    component: _ApplicationComponent

    def to_xml_element(self) -> Element:
        root = Element("application")
        comp_el = SubElement(root, "component", {"name": self.component.name})
        mapping_el = SubElement(comp_el, "mapping")
        for schema in self.component.yaml_schema_mappings.mapping:
            SubElement(mapping_el, "tooling", {"file": schema.file, "pattern": schema.pattern})
        return root

    def write_xml(self, path: Path):
        """Write pretty-printed XML to the given path"""
        path.parent.mkdir(parents=True, exist_ok=True)
        xml_str = tostring(self.to_xml_element(), encoding="utf-8")

        # Pretty-print with minidom
        parsed = minidom.parseString(xml_str)
        pretty_xml_str = parsed.toprettyxml(indent="  ", encoding="utf-8")

        # Write to file
        path.write_bytes(pretty_xml_str)


def write_jetbrains_schemas(src_schemas_dir: Path, idea_dir: Path):
    """
    Install mgtest YAML schemas for JetBrains IDEs using .idea/fileTypes/.

    Args:
        src_schemas_dir: Path where generated mgtest resource and test schemas are stored.
        idea_dir: Path to the project's .idea directory.
    """
    if idea_dir.name != ".idea":
        idea_dir = idea_dir / ".idea"
    idea_dir.mkdir(parents=True, exist_ok=True)

    # Copy schemas to a stable location inside project
    tgt_schemas_dir = idea_dir / "mgtest_schemas"
    shutil.copytree(src_schemas_dir, tgt_schemas_dir, dirs_exist_ok=True)

    # Create the required directories inside .idea
    filetypes_dir = idea_dir / "fileTypes"
    filetypes_dir.mkdir(parents=True, exist_ok=True)
    idea_file = filetypes_dir / "mgtest_schemas.xml"
    idea_file.parent.mkdir(parents=True, exist_ok=True)

    def relative_schemas(filename):
        return f"$PROJECT_DIR$/{tgt_schemas_dir.relative_to(idea_dir.parent).as_posix()}/{filename}"

    app = _Application(
        component=_ApplicationComponent(
            name="YAMLSchemaMappings",
            yaml_schema_mappings=_YAMLSchemaMappings(
                mapping=[
                    *[
                        _SchemaMapping(file=relative_schemas("resource.json"), pattern=pattern)
                        for pattern in RESOURCE_GLOBS
                    ],
                    *[
                        _SchemaMapping(file=relative_schemas("test.json"), pattern=pattern)
                        for pattern in TEST_GLOBS
                    ],
                ]
            ),
        )
    )

    # Write the XML
    app.write_xml(idea_file)
    logger.info("Installed JetBrains schemas in %s", idea_dir)

    return 0
