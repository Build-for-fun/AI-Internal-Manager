"""Document chunking for embedding generation."""

import re
from dataclasses import dataclass
from typing import Any

import tiktoken


@dataclass
class Chunk:
    """A chunk of text with metadata."""

    text: str
    metadata: dict[str, Any]
    start_idx: int
    end_idx: int
    token_count: int


class DocumentChunker:
    """Chunks documents for embedding generation.

    Uses multiple strategies:
    - Semantic chunking (splits on paragraph/section boundaries)
    - Token-based chunking with overlap
    - Recursive character splitting as fallback
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        model: str = "cl100k_base",  # Default tokenizer for OpenAI/Anthropic
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding(model)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def chunk_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Chunk text into smaller pieces.

        Tries semantic chunking first, falls back to token-based splitting.
        """
        metadata = metadata or {}

        # Try semantic chunking first
        chunks = self._semantic_chunk(text, metadata)

        # If chunks are too large, split them further
        final_chunks = []
        for chunk in chunks:
            if chunk.token_count <= self.chunk_size:
                final_chunks.append(chunk)
            else:
                # Split large chunks with overlap
                sub_chunks = self._token_chunk(
                    chunk.text,
                    {**metadata, **chunk.metadata},
                    chunk.start_idx,
                )
                final_chunks.extend(sub_chunks)

        return final_chunks

    def _semantic_chunk(
        self,
        text: str,
        metadata: dict[str, Any],
    ) -> list[Chunk]:
        """Split text on semantic boundaries (paragraphs, sections)."""
        chunks = []

        # Split on double newlines (paragraphs) or markdown headers
        patterns = [
            r'\n\n+',  # Double newlines
            r'\n#{1,6}\s',  # Markdown headers
            r'\n---+\n',  # Horizontal rules
        ]

        combined_pattern = '|'.join(f'({p})' for p in patterns)
        parts = re.split(combined_pattern, text)

        # Filter out None and separator matches, recombine
        clean_parts = []
        current_part = ""
        for part in parts:
            if part is None:
                continue
            if re.match(r'^\n+$|^---+$', part):
                # This is a separator, add to current part
                if current_part:
                    clean_parts.append(current_part)
                    current_part = ""
            elif re.match(r'^#{1,6}\s', part):
                # This is a header, start new part
                if current_part:
                    clean_parts.append(current_part)
                current_part = part
            else:
                current_part += part

        if current_part:
            clean_parts.append(current_part)

        # Create chunks
        current_idx = 0
        for part in clean_parts:
            part = part.strip()
            if not part:
                continue

            token_count = self.count_tokens(part)
            start_idx = text.find(part, current_idx)
            end_idx = start_idx + len(part)

            chunks.append(Chunk(
                text=part,
                metadata=metadata,
                start_idx=start_idx,
                end_idx=end_idx,
                token_count=token_count,
            ))

            current_idx = end_idx

        return chunks

    def _token_chunk(
        self,
        text: str,
        metadata: dict[str, Any],
        base_idx: int = 0,
    ) -> list[Chunk]:
        """Split text based on token count with overlap."""
        chunks = []
        tokens = self.tokenizer.encode(text)

        if len(tokens) <= self.chunk_size:
            return [Chunk(
                text=text,
                metadata=metadata,
                start_idx=base_idx,
                end_idx=base_idx + len(text),
                token_count=len(tokens),
            )]

        # Split with overlap
        start = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)

            # Find the actual position in the original text
            chunk_start_idx = base_idx + text.find(chunk_text[:50])
            chunk_end_idx = chunk_start_idx + len(chunk_text)

            chunks.append(Chunk(
                text=chunk_text,
                metadata={
                    **metadata,
                    "chunk_index": len(chunks),
                },
                start_idx=chunk_start_idx,
                end_idx=chunk_end_idx,
                token_count=len(chunk_tokens),
            ))

            # Move start with overlap
            start = end - self.chunk_overlap
            if start <= 0 and end < len(tokens):
                start = end  # Prevent infinite loop

        return chunks

    def chunk_with_context(
        self,
        text: str,
        title: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Chunk text and prepend context to each chunk.

        This helps embeddings capture document-level context.
        """
        metadata = metadata or {}
        if title:
            metadata["title"] = title
        if source:
            metadata["source"] = source

        chunks = self.chunk_text(text, metadata)

        # Prepend context to each chunk
        context_prefix = ""
        if title:
            context_prefix += f"Title: {title}\n"
        if source:
            context_prefix += f"Source: {source}\n"
        if context_prefix:
            context_prefix += "\n"

        # Update chunks with context
        for chunk in chunks:
            if context_prefix:
                chunk.text = context_prefix + chunk.text
                chunk.token_count = self.count_tokens(chunk.text)

        return chunks


# Singleton instance with default settings
chunker = DocumentChunker()
