import tiktoken


class TokenCounter:
    def __init__(self, encoding: str = "cl100k_base"):
        self._encoder = tiktoken.get_encoding(encoding)

    def count(self, text: str) -> int:
        return len(self._encoder.encode(text))

    def split_by_tokens(self, text: str, max_tokens: int, overlap: int = 0) -> list[str]:
        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return [text]

        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self._encoder.decode(chunk_tokens)
            chunks.append(chunk_text)
            start += max_tokens - overlap
            if start >= len(tokens):
                break

        return chunks

    def truncate(self, text: str, max_tokens: int) -> str:
        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self._encoder.decode(tokens[:max_tokens])
