import chromadb
from config import config

class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=config.VECTOR_DB_PATH)
        self.collection = self.client.get_or_create_collection(name="code_history")

    async def query_history(self, filename: str, content: str):
        # Basic search based on filename or snippets
        results = self.collection.query(
            query_texts=[f"{filename} {content[:200]}"],
            n_results=3
        )
        return results['documents']

    async def add_to_history(self, filename: str, analysis: str, commit_msg: str):
        self.collection.add(
            documents=[f"Commit: {commit_msg}\nAnalysis: {analysis}"],
            metadatas=[{"filename": filename, "type": "analysis"}],
            ids=[f"{filename}_{hash(analysis)}"]
        )

rag_service = RAGService()
