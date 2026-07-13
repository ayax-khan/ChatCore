import re
import math
from typing import Optional

from app.core.config import settings


class ChunkerService:
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        strategy: str = "hybrid",
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.strategy = strategy

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[dict]:
        if not text or not text.strip():
            return []
        if self.strategy == "token":
            return self._token_chunk(text, metadata)
        elif self.strategy == "sentence":
            return self._sentence_chunk(text, metadata)
        elif self.strategy == "structural":
            return self._structural_chunk(text, metadata)
        else:
            return self._hybrid_chunk(text, metadata)

    def _token_chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        words = text.split()
        if not words:
            return []
        chunks = []
        start = 0
        while start < len(words):
            end = start + self.chunk_size
            chunk_text = " ".join(words[start:end])
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": len(chunks),
                    "chunk_strategy": "token",
                    "word_count": len(chunk_text.split()),
                },
            })
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def _sentence_chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        import nltk
        import os
        nltk_data_path = os.environ.get("NLTK_DATA") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "nltk_data")
        if os.path.isdir(nltk_data_path):
            nltk.data.path.insert(0, nltk_data_path)
        try:
            sent_tokenizer = nltk.sent_tokenize
        except LookupError:
            try:
                nltk.download("punkt_tab")
            except Exception:
                pass
            sent_tokenizer = nltk.sent_tokenize

        sentences = sent_tokenizer(text)
        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sent_len = len(sentence.split())
            if current_length + sent_len > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks),
                        "chunk_strategy": "sentence",
                        "sentence_count": len(current_chunk),
                    },
                })
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length >= self.chunk_overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_length += len(s.split())
                current_chunk = overlap_sentences
                current_length = overlap_length

            current_chunk.append(sentence)
            current_length += sent_len

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": len(chunks),
                    "chunk_strategy": "sentence",
                    "sentence_count": len(current_chunk),
                },
            })
        return chunks

    def _structural_chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        sections = []
        current_heading = ""
        current_content = []
        current_level = 0
        last_pos = 0

        for match in heading_pattern.finditer(text):
            content_before = text[last_pos:match.start()].strip()
            if content_before:
                current_content.append(content_before)
            if current_content:
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "content": "\n".join(current_content).strip(),
                })
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            current_content = []
            last_pos = match.end()

        remaining = text[last_pos:].strip()
        if remaining:
            sections.append({
                "heading": current_heading,
                "level": current_level,
                "content": remaining,
            })

        if not sections:
            return self._sentence_chunk(text, metadata)

        chunks = []
        for section in sections:
            if not section["content"]:
                continue
            section_text = section["content"]
            section_heading = section["heading"]
            section_level = section["level"]

            if len(section_text.split()) > self.chunk_size:
                meta = {
                    **(metadata or {}),
                    "section": section_heading,
                    "heading_level": section_level,
                }
                sub_chunks = self._sentence_chunk(section_text, meta)
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    "content": section_text,
                    "metadata": {
                        **(metadata or {}),
                        "section": section_heading,
                        "heading_level": section_level,
                        "chunk_strategy": "structural",
                    },
                })
        return chunks

    def _hybrid_chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        structural = self._structural_chunk(text, metadata)
        if len(structural) > 1 or (len(structural) == 1 and len(structural[0]["content"].split()) <= self.chunk_size):
            for chunk in structural:
                chunk["metadata"]["chunk_strategy"] = "hybrid"
            return structural
        return self._sentence_chunk(text, metadata)

    def split_document(self, file_path: str, metadata: dict | None = None) -> list[dict]:
        from app.services.document_parser import DocumentParserService
        parser = DocumentParserService()
        text = parser.parse_file(file_path)
        if not text:
            return []
        doc_meta = {
            **(metadata or {}),
            "source_file": file_path,
            "source_type": "file",
        }
        return self.chunk_text(text, doc_meta)

    def split_website_page(self, title: str, content: str, url: str, metadata: dict | None = None) -> list[dict]:
        meta = {
            "url": url,
            "title": title,
            "source_type": "webpage",
            **(metadata or {}),
        }
        return self.chunk_text(content, meta)
