from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser, Node

import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
import tree_sitter_java
import tree_sitter_go
import tree_sitter_rust
import tree_sitter_cpp
import tree_sitter_c
import tree_sitter_ruby
import tree_sitter_php

from app.models.schemas import CodeSymbol, ParsedFile
from app.utils.file_utils import should_include, detect_language

LANGUAGE_LOADER = {
    "python": tree_sitter_python,
    "javascript": tree_sitter_javascript,
    "typescript": tree_sitter_typescript,
    "java": tree_sitter_java,
    "go": tree_sitter_go,
    "rust": tree_sitter_rust,
    "cpp": tree_sitter_cpp,
    "c": tree_sitter_c,
    "ruby": tree_sitter_ruby,
    "php": tree_sitter_php,
}

NODE_TYPE_MAP = {
    "function_definition": "function",
    "method_definition": "method",
    "class_definition": "class",
    "class_declaration": "class",
    "function_declaration": "function",
    "method_declaration": "method",
    "import_statement": "import",
    "import_from_statement": "import",
    "import_declaration": "import",
    "require_statement": "import",
    "source_file": "import",
}


class ParserService:
    def __init__(self):
        self._parsers: dict[str, Parser] = {}

    def _get_parser(self, language: str) -> Optional[Parser]:
        if language in self._parsers:
            return self._parsers[language]

        loader = LANGUAGE_LOADER.get(language)
        if not loader:
            return None

        try:
            lang = Language(loader.language())
            parser = Parser()
            parser.language = lang
            self._parsers[language] = parser
            return parser
        except Exception:
            return None

    def _extract_symbols(self, node: Node, code: bytes, language: str) -> list[CodeSymbol]:
        symbols = []
        self._walk_tree(node, code, language, symbols)
        return symbols

    def _walk_tree(self, node: Node, code: bytes, language: str, symbols: list[CodeSymbol]):
        node_type = node.type
        symbol_type = NODE_TYPE_MAP.get(node_type)

        if symbol_type:
            name = self._get_node_name(node, language)
            if name or symbol_type == "import":
                docstring = self._get_docstring(node, code)
                symbols.append(
                    CodeSymbol(
                        name=name or node_type,
                        type=symbol_type,
                        code=code[node.start_byte:node.end_byte].decode("utf-8", errors="replace"),
                        file_path="",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        language=language,
                        docstring=docstring,
                    )
                )

        for child in node.children:
            self._walk_tree(child, code, language, symbols)

    def _get_node_name(self, node: Node, language: str) -> Optional[str]:
        if language == "python":
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
        elif language in ("javascript", "typescript"):
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
            declarator = node.child_by_field_name("declarator")
            if declarator:
                name_node = declarator.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf-8") if name_node.text else None
        elif language == "go":
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
        elif language == "rust":
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
        elif language == "java":
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
        elif language == "cpp":
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
        elif language == "c":
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
        elif language == "ruby":
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
        elif language == "php":
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8") if name_node.text else None
        return None

    def _get_docstring(self, node: Node, code: bytes) -> Optional[str]:
        if not node.children:
            return None
        first_child = node.children[0]
        if first_child.type in ("comment", "doc_comment", "block_comment", "line_comment"):
            return code[first_child.start_byte:first_child.end_byte].decode("utf-8", errors="replace")
        if first_child.type == "expression_statement" and first_child.children:
            inner = first_child.children[0]
            if inner.type == "string":
                return code[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
        if node.type in ("function_definition", "method_definition"):
            for child in node.children:
                if child.type in ("block", "body"):
                    if child.children:
                        first_in_block = child.children[0]
                        if first_in_block.type == "expression_statement" and first_in_block.children:
                            inner = first_in_block.children[0]
                            if inner.type == "string":
                                return code[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
        return None

    def _parse_with_tree_sitter(self, file_path: Path, language: str) -> ParsedFile:
        code = file_path.read_bytes()
        parser = self._get_parser(language)
        if not parser:
            return self._fallback_parse(file_path, language)

        tree = parser.parse(code)
        if not tree or not tree.root_node:
            return self._fallback_parse(file_path, language)

        symbols = self._extract_symbols(tree.root_node, code, language)
        for sym in symbols:
            sym.file_path = str(file_path)
        return ParsedFile(
            file_path=str(file_path),
            language=language,
            symbols=symbols,
        )

    def _fallback_parse(self, file_path: Path, language: str) -> ParsedFile:
        code = file_path.read_text("utf-8", errors="replace")
        lines = code.split("\n")
        symbols = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("def ", "class ", "function ", "func ")):
                name = stripped.split("(")[0].split(" ")[-1].split(":")[0]
                symbols.append(
                    CodeSymbol(
                        name=name,
                        type="function" if not stripped.startswith("class ") else "class",
                        code=line,
                        file_path=str(file_path),
                        start_line=i,
                        end_line=i,
                        language=language,
                    )
                )
        return ParsedFile(
            file_path=str(file_path),
            language=language,
            symbols=symbols,
        )

    def parse_repo(self, repo_path: str) -> list[ParsedFile]:
        root = Path(repo_path)
        if not root.exists():
            raise FileNotFoundError(f"Repo path not found: {repo_path}")

        parsed_files = []
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file() or not should_include(file_path):
                continue
            language = detect_language(file_path)
            if language == "unknown":
                continue
            parsed = self._parse_with_tree_sitter(file_path, language)
            parsed_files.append(parsed)
        return parsed_files
