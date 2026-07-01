import asyncio
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

from openai import AsyncOpenAI
import structlog

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.models.schemas import Message, RagResponse

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are a code assistant that answers questions about a GitHub repository.
You will receive the user's question, relevant code context, and past conversation history.

## CORE RULES

1. **Answer ONLY from the provided context.** If the context doesn't contain the answer, say "I couldn't find information about that in this codebase" — do not make things up.
2. **Reference files and line numbers** in every answer using `file_path:line_number` format.
3. **No preamble.** Start directly with the answer. Do not say "Based on the code context..." or "Here's the answer..." or rephrase the question.
4. **Be concise and technical.** Prioritize accuracy over verbosity. Use bullet points for multiple facts.
5. **Match the user's language.** If they ask in English, answer in English. If they ask in Spanish, answer in Spanish.

## FORMATTING

- Use markdown: `inline code` for file paths and symbols, **bold** for emphasis, ```language for code blocks.
- Use ## headings for major sections when the answer covers multiple topics.
- End every file reference with its line range like `src/auth.py:42-51`.
- When showing code, include the file path and line numbers as a comment or citation.
- Do NOT wrap your entire response in ```markdown fences. Just output the markdown content directly.

## EXAMPLE

User: How does authentication work?
Assistant: Authentication is handled by `AuthMiddleware` in `src/auth.py:10-45`. It validates JWT tokens using the `verify_token()` function:

- `src/auth.py:42-51` — `verify_token()` decodes the JWT, checks expiry, and returns the payload
- `src/auth.py:55-60` — `AuthMiddleware` class applies the middleware to all `/api/*` routes
- `src/models/user.py:12-20` — `User` model stores hashed passwords

The middleware raises a 401 error if the token is missing or expired (`src/auth.py:48`).

## Code Context:
{context}

## Conversation History:
{history}

## User Question:
{question}

## Answer:"""


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> str:
        ...

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: str) -> AsyncGenerator[str, None]:
        ...


class OpenAILLM(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    def generate(self, prompt: str, system_prompt: str) -> str:
        import openai
        sync = openai.OpenAI(api_key=settings.openai_api_key)
        response = sync.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    async def generate_stream(self, prompt: str, system_prompt: str) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content


class RagService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService()
        self._llm: LLMProvider = OpenAILLM()

    @property
    def llm(self) -> LLMProvider:
        return self._llm

    def set_llm(self, llm: LLMProvider):
        self._llm = llm

    def answer(self, repo_id: str, question: str, history: Optional[list[Message]] = None) -> RagResponse:
        question_embedding = self.embedding_service.embed_query(question)

        results = self.vector_service.query(
            repo_id=repo_id,
            query_embedding=question_embedding,
            top_k=settings.max_context_chunks,
        )

        if not results:
            return RagResponse(
                answer="I couldn't find any relevant code in this repository to answer your question.",
                sources=[],
            )

        context_parts = []
        sources = []
        seen_files = set()
        for r in results:
            context_parts.append(r.chunk.content)
            file_key = f"{r.chunk.file_path}:{r.chunk.start_line}-{r.chunk.end_line}"
            if file_key not in seen_files:
                seen_files.add(file_key)
                sources.append({
                    "file_path": r.chunk.file_path,
                    "start_line": r.chunk.start_line,
                    "end_line": r.chunk.end_line,
                    "symbol": r.chunk.symbol_name or "",
                })

        context = "\n\n---\n\n".join(context_parts)

        history_text = ""
        if history:
            history_lines = []
            for m in history[-5:]:
                role = "User" if m.role == "user" else "Assistant"
                history_lines.append(f"{role}: {m.content}")
            history_text = "\n".join(history_lines)

        prompt = SYSTEM_PROMPT.format(
            context=context,
            history=history_text or "No previous conversation.",
            question=question,
        )

        answer = self._llm.generate(prompt, "")
        return RagResponse(answer=answer, sources=sources)

    async def answer_stream(
        self, repo_id: str, question: str, history: Optional[list[Message]] = None
    ) -> AsyncGenerator[str, None]:
        question_embedding = await asyncio.to_thread(self.embedding_service.embed_query, question)

        results = await asyncio.to_thread(
            self.vector_service.query,
            repo_id, question_embedding, settings.max_context_chunks,
        )

        if not results:
            yield json.dumps({"type": "chunk", "content": "I couldn't find any relevant code in this repository to answer your question."})
            yield json.dumps({"type": "done"})
            return

        context_parts = []
        sources = []
        seen_files = set()
        for r in results:
            context_parts.append(r.chunk.content)
            file_key = f"{r.chunk.file_path}:{r.chunk.start_line}-{r.chunk.end_line}"
            if file_key not in seen_files:
                seen_files.add(file_key)
                sources.append({
                    "file_path": r.chunk.file_path,
                    "start_line": r.chunk.start_line,
                    "end_line": r.chunk.end_line,
                    "symbol": r.chunk.symbol_name or "",
                })

        context = "\n\n---\n\n".join(context_parts)

        history_text = ""
        if history:
            history_lines = []
            for m in history[-5:]:
                role = "User" if m.role == "user" else "Assistant"
                history_lines.append(f"{role}: {m.content}")
            history_text = "\n".join(history_lines)

        prompt = SYSTEM_PROMPT.format(
            context=context,
            history=history_text or "No previous conversation.",
            question=question,
        )

        yield json.dumps({"type": "sources", "sources": sources})

        async for token in self._llm.generate_stream(prompt, ""):
            yield json.dumps({"type": "chunk", "content": token})

        yield json.dumps({"type": "done"})
