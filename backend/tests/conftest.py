import os

# Keep pytest from overwriting the developer FAISS index on disk.
os.environ.setdefault("ECORAG_INDEX_PERSIST", "false")

TEST_API_KEY = "test-only-ecorag-api-key-not-for-production"
TEST_AUTH_HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}

os.environ["ECORAG_API_KEY"] = TEST_API_KEY
os.environ["ECORAG_API_SCOPES"] = "read,write,tools:invoke"
os.environ["ECORAG_API_USER_ID"] = "local-user"
os.environ["SECURITY_QUERY_REQUESTS_PER_WINDOW"] = "1000"
os.environ["SECURITY_SEARCH_REQUESTS_PER_WINDOW"] = "1000"
os.environ["SECURITY_INGESTION_REQUESTS_PER_WINDOW"] = "1000"
