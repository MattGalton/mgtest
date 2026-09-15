from pathlib import Path

from lsprotocol import types
from pygls.lsp.server import LanguageServer

server = LanguageServer("example-server", "v0.1")

ALLOWED_EXTENSIONS = (".r.yml", ".t.yml")


def is_allowed(uri: str) -> bool:
    path = Path(uri.replace("file://", ""))
    return path.name.endswith(ALLOWED_EXTENSIONS)


@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def completions(params: types.CompletionParams):

    if not is_allowed(params.text_document.uri):
        return types.CompletionList(is_incomplete=False, items=[])

    items = []
    document = server.workspace.get_text_document(params.text_document.uri)
    current_line = document.lines[params.position.line].strip()
    if current_line.endswith("hello."):
        items = [
            types.CompletionItem(label="world"),
            types.CompletionItem(label="friend"),
        ]
    return types.CompletionList(is_incomplete=False, items=items)


server.start_io()
