import re
from pathlib import Path

from app.config import settings
from app.models.schemas import CodeChunk, ParsedFile, CodeSymbol
from app.utils.token_utils import TokenCounter


class ChunkerService:
    def __init__(self):
        self.token_counter = TokenCounter()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    def chunk_parsed_files(self, parsed_files: list[ParsedFile], repo_id: str) -> list[CodeChunk]:
        chunks: list[CodeChunk] = []
        for pf in parsed_files:
            lang = pf.language
            if lang in ("markdown", "text", "yaml", "json", "toml"):
                file_chunks = self._chunk_document_file(pf, repo_id)
            else:
                file_chunks = self._chunk_code_file(pf, repo_id)
            chunks.extend(file_chunks)
        return chunks

    def _chunk_code_file(self, pf: ParsedFile, repo_id: str) -> list[CodeChunk]:
        chunks: list[CodeChunk] = []

        for sym in pf.symbols:
            header = self._build_context_header(pf.file_path, pf.language, sym)

            body = sym.code
            full_text = header + body

            tokens = self.token_counter.count(full_text)
            if tokens <= self.chunk_size:
                chunks.append(CodeChunk(
                    repo_id=repo_id,
                    file_path=pf.file_path,
                    language=pf.language,
                    symbol_name=sym.name,
                    symbol_type=sym.type,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    chunk_index=0,
                    content=full_text,
                ))
            else:
                sub_chunks = self.token_counter.split_by_tokens(
                    body, self.chunk_size - self.token_counter.count(header), self.chunk_overlap
                )
                for i, sub in enumerate(sub_chunks):
                    chunks.append(CodeChunk(
                        repo_id=repo_id,
                        file_path=pf.file_path,
                        language=pf.language,
                        symbol_name=sym.name,
                        symbol_type=sym.type,
                        start_line=sym.start_line,
                        end_line=sym.end_line,
                        chunk_index=i,
                        content=header + sub,
                    ))

        return chunks

    def _chunk_document_file(self, pf: ParsedFile, repo_id: str) -> list[CodeChunk]:
        chunks: list[CodeChunk] = []
        rel_path = pf.file_path

        try:
            text = Path(rel_path).read_text("utf-8", errors="replace")
        except Exception:
            if pf.symbols:
                text = "\n".join(s.code for s in pf.symbols)
            else:
                return chunks

        sections = re.split(r"(^#+ .+$)", text, flags=re.MULTILINE)
        current_section = ""
        for part in sections:
            if re.match(r"^#+ .+$", part):
                if current_section.strip():
                    chunk = current_section.strip()
                    if self.token_counter.count(chunk) <= self.chunk_size:
                        chunks.append(CodeChunk(
                            repo_id=repo_id,
                            file_path=rel_path,
                            language=pf.language,
                            symbol_name="documentation",
                            symbol_type="doc",
                            start_line=1,
                            end_line=1,
                            content=chunk,
                        ))
                    else:
                        sub = self.token_counter.split_by_tokens(chunk, self.chunk_size, self.chunk_overlap)
                        for i, s in enumerate(sub):
                            chunks.append(CodeChunk(
                                repo_id=repo_id,
                                file_path=rel_path,
                                language=pf.language,
                                symbol_name="documentation",
                                symbol_type="doc",
                                start_line=1,
                                end_line=1,
                                chunk_index=i,
                                content=s,
                            ))
                    current_section = ""
                current_section = part + "\n"
            else:
                current_section += part

        if current_section.strip():
            chunk = current_section.strip()
            if self.token_counter.count(chunk) <= self.chunk_size:
                chunks.append(CodeChunk(
                    repo_id=repo_id,
                    file_path=rel_path,
                    language=pf.language,
                    symbol_name="documentation",
                    symbol_type="doc",
                    start_line=1,
                    end_line=1,
                    content=chunk,
                ))
            else:
                sub = self.token_counter.split_by_tokens(chunk, self.chunk_size, self.chunk_overlap)
                for i, s in enumerate(sub):
                    chunks.append(CodeChunk(
                        repo_id=repo_id,
                        file_path=rel_path,
                        language=pf.language,
                        symbol_name="documentation",
                        symbol_type="doc",
                        start_line=1,
                        end_line=1,
                        chunk_index=i,
                        content=s,
                    ))

        if not chunks:
            chunks.append(CodeChunk(
                repo_id=repo_id,
                file_path=rel_path,
                language=pf.language,
                symbol_name="documentation",
                symbol_type="doc",
                start_line=1,
                end_line=1,
                content=text,
            ))

        return chunks

    def _build_context_header(self, file_path: str, language: str, sym: CodeSymbol) -> str:
        return (
            f"File: {file_path}\n"
            f"Language: {language}\n"
            f"Type: {sym.type}\n"
            f"Name: {sym.name}\n"
            f"Lines: {sym.start_line}-{sym.end_line}\n"
            f"---\n"
        )
