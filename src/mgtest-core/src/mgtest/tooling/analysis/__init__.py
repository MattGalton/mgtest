"""Editor-independent analysis for mgtest YAML documents.

The public API remains here so CLI and LSP adapters do not depend on the internal
feature modules.
"""

from mgtest.project.layout import ProjectLayout

from .cli import main
from .service import AnalysisService
from .types import Diagnostic

is_mgtest_path = ProjectLayout.is_mgtest_document

__all__ = ["AnalysisService", "Diagnostic", "is_mgtest_path", "main"]
