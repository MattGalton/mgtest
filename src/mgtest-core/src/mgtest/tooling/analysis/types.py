"""Protocol-neutral values and lexical rules used by mgtest analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass

REFERENCE = re.compile(r"\$\{(?:mgtest:)?(?P<kind>resources|tests)\.(?P<name>[^.}]+)")
REFERENCE_VALUE = re.compile(
    r"\$\{(?:mgtest:)?(?:(?P<variable_kind>vars)\.(?P<variable>[^.}]+)|"
    r"(?P<kind>resources|tests)\.(?P<name>[^.}]+)(?:\.outputs\.(?P<output>[^.}]+))?)\}"
)
OMEGACONF_RESOLVERS = {
    "oc.env": "Read an environment variable: `${oc.env:NAME}` or `${oc.env:NAME,default}`.",
    "oc.decode": "Parse a string value using OmegaConf grammar: `${oc.decode:'[1, 2]'}`.",
    "oc.create": "Create a configuration node from a value: `${oc.create:{key: value}}`.",
    "oc.select": "Select a configuration value safely: `${oc.select:path.to.value,default}`.",
    "oc.dict.keys": "Return the keys of a configuration mapping: `${oc.dict.keys:my_map}`.",
    "oc.dict.values": "Return the values of a configuration mapping: `${oc.dict.values:my_map}`.",
}


@dataclass(frozen=True)
class Diagnostic:
    message: str
    line: int = 0
    character: int = 0
    end_line: int = 0
    end_character: int = 1
    severity: int = 1
    code: str = "mgtest"
