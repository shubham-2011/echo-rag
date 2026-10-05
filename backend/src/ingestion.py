import os
import hashlib
import re
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field

import io
import logging

logger = logging.getLogger(__name__)

PAGE_MARKER_RE = re.compile(r"---\s*Page\s+(\d+)\s*---", re.I)
KNOWN_SECTIONS = [
    "About Us",
    "Who are we",
    "What Do We Do",
    "Job Specification & Employment Details",
    "Required Technical Skillset",
    "Work Location",
    "Role & Responsibilities",
    "Eligibility Criteria",
    "Internship Details",
    "Full-Time Employment Terms",
    "Interview Selection Process",
    "Round 1",
    "Round 2",
    "Round 3",
    "Synoptek Promise",
    "Legal Notice",
    "JOB DESCRIPTION",
    "Job Description",
    "Role at a Glance",
    "Project Context",
    "Key Responsibilities",
    "Skills Required",
    "Educational Qualifications",
]

KNOWN_SUBSECTIONS = [
    "Degree Requirement",
    "Academic Performance",
    "Annual Compensation",
    "Commitment Period",
    "Bond Clause",
    "Early Exit Clause",
    "Duration",
    "Stipend",
    "Shift",
    "Performance-Based Confirmation",
]


def _heading_regex(titles: list[str]) -> re.Pattern:
    escaped = "|".join(re.escape(t) for t in sorted(titles, key=len, reverse=True))
    return re.compile(
        rf"(?:^|\n|[•])\s*(?:[•\-\*]+\s*)?({escaped})\??\s*:?\s*",
        re.I,
    )


SECTION_SPLIT_RE = _heading_regex(KNOWN_SECTIONS)
SUBSECTION_RE = _heading_regex(KNOWN_SUBSECTIONS)
SECTION_RE = re.compile(
    rf"({ '|'.join(re.escape(t) for t in KNOWN_SECTIONS) })",
    re.I,
)


def parse_page_number(text: str, metadata: Optional[Dict[str, Any]] = None, parent_text: Optional[str] = None) -> Optional[int]:
    if metadata:
        for key in ("page", "page_number"):
            val = metadata.get(key)
            if val is None or val == "":
                continue
            try:
                return int(val)
            except (TypeError, ValueError):
                continue
    match = PAGE_MARKER_RE.search(text or "")
    if match:
        return int(match.group(1))
    if parent_text and text:
        needle = text[:80]
        idx = parent_text.find(needle) if needle else -1
        if idx >= 0:
            matches = list(PAGE_MARKER_RE.finditer(parent_text[:idx + 1]))
            if matches:
                return int(matches[-1].group(1))
    return None


def enrich_chunk_metadata(chunk: "Chunk") -> "Chunk":
    """Fill filename, file type, page, and section without overwriting existing values."""
    meta = dict(chunk.metadata or {})
    if not meta.get("filename"):
        meta["filename"] = chunk.doc_id
    if not meta.get("file_type"):
        ext = os.path.splitext(str(chunk.doc_id))[1].lstrip(".").lower()
        if ext:
            meta["file_type"] = ext
    page = parse_page_number(chunk.text, meta)
    if page is not None:
        meta["page"] = page
        meta["page_number"] = page
    if not meta.get("section"):
        section_match = SECTION_RE.search(chunk.text or "")
        if section_match:
            meta["section"] = section_match.group(1)
    if not meta.get("parent_section") and meta.get("section"):
        meta["parent_section"] = meta["section"]
    chunk.metadata = meta
    return chunk


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Extracts clean readable text from various file formats (.pdf, .docx, .txt, .md, .csv).
    Eliminates binary stream ingestion and %PDF-1.7 bytecode corruption.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    pages_text.append(f"--- Page {i + 1} ---\n{txt.strip()}")
            extracted = "\n\n".join(pages_text)
            if extracted.strip():
                return extracted
        except Exception as e:
            logger.warning("pypdf extraction failed for %s: %s", filename, e)

        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages_text = []
            for i, page in enumerate(doc):
                txt = page.get_text() or ""
                if txt.strip():
                    pages_text.append(f"--- Page {i + 1} ---\n{txt.strip()}")
            extracted = "\n\n".join(pages_text)
            if extracted.strip():
                return extracted
        except Exception as e:
            logger.warning("fitz extraction failed for %s: %s", filename, e)

    elif ext in [".docx", ".doc"]:
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            extracted = "\n\n".join(paragraphs)
            if extracted.strip():
                return extracted
        except Exception as e:
            logger.warning("docx extraction failed for %s: %s", filename, e)

    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="ignore")



@dataclass
class Chunk:
    """Represents a text chunk produced during document ingestion."""
    text: str
    chunk_id: str
    doc_id: str
    chunk_index: int
    char_length: int
    token_count_approx: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Represents a source document."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ParentDocumentStore:
    """
    In-memory registry mapping chunks to their parent document and sentence arrays.
    Enables Sentence-Window Expansion (+/- W sentences) and Parent-Document Retrieval
    to eliminate semantic fragmentation without prompt bloating.
    """
    _instance: Optional['ParentDocumentStore'] = None

    def __init__(self):
        self._documents: Dict[str, str] = {}
        self._sentences: Dict[str, List[str]] = {}

    @classmethod
    def get_instance(cls) -> 'ParentDocumentStore':
        if cls._instance is None:
            cls._instance = ParentDocumentStore()
        return cls._instance

    def register_document(self, doc_id: str, content: str, sentences: Optional[List[str]] = None) -> None:
        self._documents[doc_id] = content
        if sentences is not None:
            self._sentences[doc_id] = sentences
        else:
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if s.strip()]
            self._sentences[doc_id] = sents

    def get_document(self, doc_id: str) -> Optional[str]:
        return self._documents.get(doc_id)

    def get_sentences(self, doc_id: str) -> List[str]:
        return self._sentences.get(doc_id, [])

    def expand_window(
        self,
        doc_id: str,
        start_sentence_idx: int,
        end_sentence_idx: int,
        window: int = 2
    ) -> str:
        sents = self._sentences.get(doc_id, [])
        if not sents:
            return self._documents.get(doc_id, '')

        w_start = max(0, start_sentence_idx - window)
        w_end = min(len(sents), end_sentence_idx + window + 1)
        return ' '.join(sents[w_start:w_end])

    def clear(self) -> None:
        self._documents.clear()
        self._sentences.clear()


class TextChunker:
    """
    Configurable document chunker for EcoRAG experiments.
    Supports varying chunk sizes (e.g., 128, 256, 512, 1024 tokens) and sliding window overlap.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: Document) -> List[Chunk]:
        """Split document content into overlapping chunks based on words/tokens."""
        words = doc.content.split()
        if not words:
            return []

        chunks: List[Chunk] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        chunk_idx = 0

        for i in range(0, len(words), step):
            chunk_words = words[i: i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:12]
            chunk_id = f"{doc.doc_id}_c{chunk_idx}_{chunk_hash}"

            chunk = Chunk(
                text=chunk_text,
                chunk_id=chunk_id,
                doc_id=doc.doc_id,
                chunk_index=chunk_idx,
                char_length=len(chunk_text),
                token_count_approx=len(chunk_words),
                metadata={
                    **doc.metadata,
                    "chunk_size_config": self.chunk_size,
                    "chunk_overlap_config": self.chunk_overlap,
                }
            )
            enrich_chunk_metadata(chunk)
            chunks.append(chunk)
            chunk_idx += 1

            if i + self.chunk_size >= len(words):
                break

        return chunks


class HeadingAwareChunker:
    """Keep PDF/JD heading + bullet groups together instead of flattening across sections."""

    def chunk_document(self, doc: Document) -> List[Chunk]:
        text = doc.content or ""
        matches = list(SECTION_SPLIT_RE.finditer(text))
        if not matches:
            flat = re.compile(
                "|".join(re.escape(t) for t in sorted(KNOWN_SECTIONS, key=len, reverse=True)),
                re.I,
            )
            matches = list(flat.finditer(text))
        if not matches:
            return []

        regions: List[Tuple[str, str, int, int, int]] = []
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                regions.append(("Preamble", preamble, 0, 0, matches[0].start()))
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[match.end() : end].strip()
            title = match.group(1).strip() if match.lastindex else match.group(0).strip()
            page = parse_page_number(text[max(0, match.start() - 80) : end], doc.metadata, text)
            regions.append((title, body, page or 0, match.start(), end))

        chunks: List[Chunk] = []
        for title, body, page, _start, _end in regions:
            for parent, sub, block in self._section_units(title, body):
                chunk_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()[:12]
                chunk = Chunk(
                    text=block,
                    chunk_id=f"{doc.doc_id}_sec{len(chunks)}_{chunk_hash}",
                    doc_id=doc.doc_id,
                    chunk_index=len(chunks),
                    char_length=len(block),
                    token_count_approx=len(block.split()),
                    metadata={
                        **doc.metadata,
                        "section": parent,
                        "subsection": sub,
                        "parent_section": parent,
                        "page": page or None,
                        "page_number": page or None,
                        "context_strategy": "heading",
                    },
                )
                enrich_chunk_metadata(chunk)
                chunks.append(chunk)
        return chunks

    @staticmethod
    def _section_units(title: str, body: str) -> List[Tuple[str, Optional[str], str]]:
        padded = "\n" + (body or "")
        subs = list(SUBSECTION_RE.finditer(padded))
        if len(subs) < 2:
            sub = subs[0].group(1).strip() if subs else None
            block = f"{title}:\n{body}".strip() if body else title
            return [(title, sub, block)]

        units: List[Tuple[str, Optional[str], str]] = []
        intro = padded[1 : subs[0].start()].strip()
        for i, match in enumerate(subs):
            end = subs[i + 1].start() if i + 1 < len(subs) else len(padded)
            sub = match.group(1).strip()
            sub_body = padded[match.end() : end].strip()
            text = f"{title} / {sub}:\n{sub_body}".strip()
            if i == 0 and intro:
                text = f"{title}:\n{intro}\n{sub}:\n{sub_body}".strip()
            units.append((title, sub, text))
        return units


FIELD_LABEL_RE = re.compile(
    r"(?:^|\n)\s*(Company|Department|Team|Position Title|Location|Employment Type|"
    r"Shift|Experience|Industry|Role Type)\s+([^\n]+)",
    re.I,
)


class FieldRowChunker:
    """Keep labeled JD rows such as 'Company …' as retrieval units."""

    def chunk_document(self, doc: Document) -> List[Chunk]:
        text = doc.content or ""
        matches = list(FIELD_LABEL_RE.finditer(text))
        if len(matches) < 3:
            return []
        lines = [f"{m.group(1).strip()}: {m.group(2).strip()}" for m in matches]
        overview = "Role at a Glance\n" + "\n".join(lines)
        chunks: List[Chunk] = []

        def _make(block: str, section: str, sub: Optional[str]) -> Chunk:
            chunk_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()[:12]
            chunk = Chunk(
                text=block,
                chunk_id=f"{doc.doc_id}_fld{len(chunks)}_{chunk_hash}",
                doc_id=doc.doc_id,
                chunk_index=len(chunks),
                char_length=len(block),
                token_count_approx=len(block.split()),
                metadata={
                    **doc.metadata,
                    "section": section,
                    "subsection": sub,
                    "parent_section": section,
                    "context_strategy": "field_row",
                },
            )
            enrich_chunk_metadata(chunk)
            return chunk

        chunks.append(_make(overview, "Role at a Glance", None))
        for label, value in [(m.group(1).strip(), m.group(2).strip()) for m in matches]:
            chunks.append(_make(f"{label}: {value}", "Role at a Glance", label))
        rest = text[matches[-1].end() :].strip()
        if rest:
            rest_doc = Document(doc_id=doc.doc_id, content=rest, metadata=doc.metadata)
            for extra in SentenceWindowChunker().chunk_document(rest_doc):
                extra.chunk_index = len(chunks)
                extra.chunk_id = extra.chunk_id.replace("_sw", f"_fldsw{len(chunks)}_")
                chunks.append(extra)
        return chunks


class SentenceWindowChunker:
    """
    Sentence-aware chunker designed for precision retrieval without semantic fragmentation.
    Produces small retrieval units while cataloging sentence coordinates within ParentDocumentStore.
    """

    def __init__(self, sentences_per_chunk: int = 3, sentence_overlap: int = 1):
        self.sentences_per_chunk = sentences_per_chunk
        self.sentence_overlap = sentence_overlap

    def chunk_document(self, doc: Document) -> List[Chunk]:
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', doc.content) if s.strip()]
        if not sents:
            return []

        ParentDocumentStore.get_instance().register_document(doc.doc_id, doc.content, sents)

        chunks: List[Chunk] = []
        step = max(1, self.sentences_per_chunk - self.sentence_overlap)
        chunk_idx = 0

        for i in range(0, len(sents), step):
            chunk_sents = sents[i: i + self.sentences_per_chunk]
            chunk_text = ' '.join(chunk_sents)
            chunk_hash = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()[:12]
            chunk_id = f"{doc.doc_id}_sw{chunk_idx}_{chunk_hash}"

            start_idx = i
            end_idx = min(len(sents) - 1, i + len(chunk_sents) - 1)

            chunk = Chunk(
                text=chunk_text,
                chunk_id=chunk_id,
                doc_id=doc.doc_id,
                chunk_index=chunk_idx,
                char_length=len(chunk_text),
                token_count_approx=len(chunk_text.split()),
                metadata={
                    **doc.metadata,
                    "sentence_start_idx": start_idx,
                    "sentence_end_idx": end_idx,
                    "total_sentences": len(sents),
                    "parent_doc_id": doc.doc_id,
                    "context_strategy": "sentence_window",
                }
            )
            enrich_chunk_metadata(chunk)
            chunks.append(chunk)
            chunk_idx += 1

            if i + self.sentences_per_chunk >= len(sents):
                break

        return chunks


class ChunkDeduplicator:
    """
    Filters exact duplicate and near-duplicate chunks before vector embedding calculation.
    Saves substantial embedding compute and vector memory, while tracking net energy savings.
    """

    def __init__(self, jaccard_threshold: float = 0.90):
        self.jaccard_threshold = jaccard_threshold
        self.seen_exact_hashes: Set[str] = set()
        self.seen_shingle_sets: List[Set[str]] = []
        self.total_duplicates_filtered: int = 0
        self.total_dedup_time_ms: float = 0.0

    def _get_shingles(self, text: str, k: int = 3) -> Set[str]:
        words = re.findall(r"\w+", text.lower())
        if len(words) < k:
            return set(words)
        return {" ".join(words[i:i+k]) for i in range(len(words) - k + 1)}

    def is_duplicate(self, text: str) -> bool:
        t0 = time.perf_counter()
        h = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        if h in self.seen_exact_hashes:
            self.total_duplicates_filtered += 1
            self.total_dedup_time_ms += (time.perf_counter() - t0) * 1000.0
            return True

        shingles = self._get_shingles(text)
        if not shingles:
            self.total_dedup_time_ms += (time.perf_counter() - t0) * 1000.0
            return False

        for seen in self.seen_shingle_sets:
            intersection = len(shingles.intersection(seen))
            union = len(shingles.union(seen))
            if union > 0 and (intersection / union) >= self.jaccard_threshold:
                self.total_duplicates_filtered += 1
                self.total_dedup_time_ms += (time.perf_counter() - t0) * 1000.0
                return True

        self.seen_exact_hashes.add(h)
        self.seen_shingle_sets.append(shingles)
        self.total_dedup_time_ms += (time.perf_counter() - t0) * 1000.0
        return False

    def deduplicate_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        unique: List[Chunk] = []
        for c in chunks:
            if not self.is_duplicate(c.text):
                unique.append(c)
        return unique

    def estimate_net_energy_saved(self, llm_joules_per_chunk: float = 0.045) -> float:
        """
        Calculate Net Energy Saved = Downstream Energy Saved - Deduplication Overhead
        """
        downstream_saved = self.total_duplicates_filtered * llm_joules_per_chunk
        dedup_overhead = (self.total_dedup_time_ms / 1000.0) * 0.045  # ~45W CPU power
        return max(0.0, downstream_saved - dedup_overhead)


class MarkdownChunker:
    """
    Structure-aware chunker for Markdown (.md) documents.
    Splits by Markdown headings (#, ##, ###) while preserving document hierarchy,
    code blocks, and tables within coherent semantic chunks.
    """

    def __init__(self, max_chunk_size: int = 512, chunk_overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: Document) -> List[Chunk]:
        lines = doc.content.splitlines()
        if not lines:
            return []

        sections: List[Dict[str, Any]] = []
        current_headers: Dict[int, str] = {}
        current_lines: List[str] = []

        header_regex = re.compile(r"^(#{1,6})\s+(.+)$")

        def flush_section(header_stack: List[str], text_lines: List[str]):
            content = "\n".join(text_lines).strip()
            if content:
                sections.append({
                    "headers": list(header_stack),
                    "content": content,
                })

        for line in lines:
            match = header_regex.match(line)
            if match:
                if current_lines:
                    current_path = [current_headers[lvl] for lvl in sorted(current_headers.keys())]
                    flush_section(current_path, current_lines)
                    current_lines = []

                level = len(match.group(1))
                title = match.group(2).strip()
                current_headers = {lvl: h for lvl, h in current_headers.items() if lvl < level}
                current_headers[level] = title
            else:
                current_lines.append(line)

        if current_lines:
            current_path = [current_headers[lvl] for lvl in sorted(current_headers.keys())]
            flush_section(current_path, current_lines)

        if not sections and doc.content.strip():
            sections.append({"headers": [doc.doc_id], "content": doc.content.strip()})

        chunks: List[Chunk] = []
        chunk_idx = 0

        for sec in sections:
            sec_headers = sec["headers"]
            header_prefix = " > ".join(sec_headers) if sec_headers else doc.doc_id
            sec_text = sec["content"]
            words = sec_text.split()

            if len(words) <= self.max_chunk_size:
                formatted_text = f"[{header_prefix}]\n{sec_text}" if header_prefix else sec_text
                chunk_hash = hashlib.sha256(formatted_text.encode("utf-8")).hexdigest()[:12]
                chunk_id = f"{doc.doc_id}_md{chunk_idx}_{chunk_hash}"
                chunks.append(
                    Chunk(
                        text=formatted_text,
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        chunk_index=chunk_idx,
                        char_length=len(formatted_text),
                        token_count_approx=len(formatted_text.split()),
                        metadata={
                            **doc.metadata,
                            "headers": sec_headers,
                            "header_path": header_prefix,
                            "is_markdown": True,
                        }
                    )
                )
                chunk_idx += 1
            else:
                step = max(1, self.max_chunk_size - self.chunk_overlap)
                for i in range(0, len(words), step):
                    sub_words = words[i: i + self.max_chunk_size]
                    sub_text = " ".join(sub_words)
                    formatted_text = f"[{header_prefix} (cont.)]\n{sub_text}" if header_prefix else sub_text
                    chunk_hash = hashlib.sha256(formatted_text.encode("utf-8")).hexdigest()[:12]
                    chunk_id = f"{doc.doc_id}_md{chunk_idx}_{chunk_hash}"
                    chunks.append(
                        Chunk(
                            text=formatted_text,
                            chunk_id=chunk_id,
                            doc_id=doc.doc_id,
                            chunk_index=chunk_idx,
                            char_length=len(formatted_text),
                            token_count_approx=len(formatted_text.split()),
                            metadata={
                                **doc.metadata,
                                "headers": sec_headers,
                                "header_path": header_prefix,
                                "is_markdown": True,
                                "sub_window": i // step,
                            }
                        )
                    )
                    chunk_idx += 1
                    if i + self.max_chunk_size >= len(words):
                        break

        return chunks


class DocumentIngestionPipeline:
    """Orchestrates document loading, chunking, and deduplication."""

    def __init__(
        self,
        chunk_size: int = 256,
        chunk_overlap: int = 30,
        enable_dedup: bool = True,
        use_markdown_chunker: bool = False,
        strategy: str = "standard"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.md_chunker = MarkdownChunker(max_chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.heading_chunker = HeadingAwareChunker()
        self.field_chunker = FieldRowChunker()
        self.sentence_chunker = SentenceWindowChunker(sentences_per_chunk=3, sentence_overlap=1)
        self.use_markdown_chunker = use_markdown_chunker
        self.strategy = strategy
        self.enable_dedup = enable_dedup
        self.deduplicator = ChunkDeduplicator() if enable_dedup else None

    def ingest_text(
        self,
        text: str,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        is_markdown: bool = False
    ) -> List[Chunk]:
        doc = Document(doc_id=doc_id, content=text, metadata=metadata or {})
        ParentDocumentStore.get_instance().register_document(doc_id, text)

        if self.strategy in {"sentence_window", "heading", "structured"}:
            headed = self.heading_chunker.chunk_document(doc)
            if headed:
                chunks = headed
            else:
                fields = self.field_chunker.chunk_document(doc)
                chunks = fields if fields else self.sentence_chunker.chunk_document(doc)
        elif is_markdown or self.use_markdown_chunker or self.strategy == "markdown":
            chunks = self.md_chunker.chunk_document(doc)
        else:
            chunks = self.chunker.chunk_document(doc)

        if self.enable_dedup and self.deduplicator:
            chunks = self.deduplicator.deduplicate_chunks(chunks)
        return chunks

    def ingest_file(self, file_path: str) -> List[Chunk]:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        doc_id = os.path.basename(file_path)
        content = extract_text_from_bytes(file_bytes, doc_id)
        is_md = file_path.lower().endswith(".md")
        ext = os.path.splitext(doc_id)[1].lstrip(".").lower()
        return self.ingest_text(
            content,
            doc_id=doc_id,
            metadata={"file_path": file_path, "filename": doc_id, "file_type": ext, "source": doc_id},
            is_markdown=is_md
        )
