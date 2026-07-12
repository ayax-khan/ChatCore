import pytest
from app.services.chunker import ChunkerService
from app.services.document_parser import DocumentParserService


class TestChunkerService:
    @pytest.fixture
    def chunker(self):
        return ChunkerService(chunk_size=100, chunk_overlap=10)

    def test_token_chunking(self, chunker):
        text = "word " * 250
        chunks = chunker._token_chunk(text)
        assert len(chunks) == 3
        assert all(len(c["content"].split()) <= 100 for c in chunks)
        assert all("chunk_strategy" in c["metadata"] for c in chunks)

    def test_sentence_chunking(self, chunker):
        text = ". ".join(["This is sentence number " + str(i) for i in range(20)]) + "."
        chunks = chunker._sentence_chunk(text)
        assert len(chunks) >= 1
        assert all("chunk_strategy" in c["metadata"] for c in chunks)

    def test_structural_chunking_with_headings(self, chunker):
        text = "# Introduction\n\nThis is the intro.\n\n# Details\n\nThese are the details.\n\n# Conclusion\n\nThis is the conclusion."
        chunks = chunker._structural_chunk(text)
        assert len(chunks) >= 1
        sections = [c["metadata"].get("section", "") for c in chunks]
        assert any("Introduction" in s for s in sections)
        assert any("Details" in s for s in sections)

    def test_empty_input(self, chunker):
        chunks = chunker.chunk_text("")
        assert chunks == []

    def test_short_input(self, chunker):
        chunks = chunker.chunk_text("Hello world")
        assert len(chunks) > 0

    def test_chunk_metadata(self, chunker):
        text = "Some content here"
        metadata = {"url": "https://example.com", "source": "test"}
        chunks = chunker.chunk_text(text, metadata)
        for c in chunks:
            assert c["metadata"]["url"] == "https://example.com"
            assert c["metadata"]["source"] == "test"

    def test_overlap_size(self, chunker):
        text = "word " * 200
        chunks = chunker._token_chunk(text)
        if len(chunks) > 1:
            first_end = set(chunks[0]["content"].split())
            second_start = set(chunks[1]["content"].split())
            assert len(first_end & second_start) <= chunker.chunk_overlap


class TestDocumentParserService:
    @pytest.fixture
    def parser(self):
        return DocumentParserService()

    def test_parse_text_file(self, parser, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world\nThis is a test file.")
        result = parser.parse_file(str(f))
        assert "Hello world" in result
        assert "test file" in result

    def test_parse_csv_text(self, parser):
        csv_data = b"name,email,role\nJohn,john@test.com,admin\nJane,jane@test.com,editor"
        result = parser.parse_bytes(csv_data, "csv")
        assert "John" in result
        assert "admin" in result

    def test_detect_language_english(self, parser):
        text = "This is a simple English text for testing language detection."
        lang = parser.detect_language(text)
        assert lang == "en"

    def test_detect_language_chinese(self, parser):
        text = "这是一段中文文本用于测试语言检测功能是否正确工作。"
        lang = parser.detect_language(text)
        assert lang == "zh"

    def test_detect_language_arabic(self, parser):
        text = "هذا نص عربي لاختبار اكتشاف اللغة."
        lang = parser.detect_language(text)
        assert lang == "ar"

    def test_unsupported_format(self, parser):
        result = parser.parse_file("file.xyz")
        assert "Unsupported" in result
