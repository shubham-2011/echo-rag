from pathlib import Path
from src.ingestion import extract_text_from_bytes, DocumentIngestionPipeline, HeadingAwareChunker, Document

pdf = Path(r"d:\job related\JDS\JD-Implementation & Support Engineer fresher.pdf")
text = extract_text_from_bytes(pdf.read_bytes(), pdf.name)
print("LEN", len(text))
print(text[:3500])
print("\n===== HEADINGS =====")
for line in text.splitlines():
    s = line.strip()
    if s and len(s) < 80:
        print(repr(s))
print("\n===== CHUNKS =====")
pipe = DocumentIngestionPipeline(strategy="sentence_window", enable_dedup=False)
chunks = pipe.ingest_text(text, doc_id=pdf.name, metadata={"filename": pdf.name})
print("n", len(chunks))
for c in chunks[:8]:
    print("---", c.chunk_id, c.metadata.get("section"), "---")
    print(c.text[:400])
    print()
