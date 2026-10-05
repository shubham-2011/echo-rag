import os

# Keep pytest from overwriting the developer FAISS index on disk.
os.environ.setdefault("ECORAG_INDEX_PERSIST", "false")
