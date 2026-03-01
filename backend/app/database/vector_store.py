from typing import List, Optional
from abc import ABC, abstractmethod
import chromadb

from app.config import settings


class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    async def add_documents(self, documents: List[dict], embeddings: List[List[float]]) -> None:
        """Add documents with their embeddings to the store."""
        pass
    
    @abstractmethod
    async def search(self, query_embedding: List[float], top_k: int = 10) -> List[dict]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    async def delete(self, ids: List[str]) -> None:
        """Delete documents by IDs."""
        pass


class ChromaVectorStore(VectorStore):
    """ChromaDB implementation for local development."""
    
    def __init__(self):
        # Use the new ChromaDB persistent client API
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(
            name="crypto_pulse",
            metadata={"hnsw:space": "cosine"},
        )
    
    async def add_documents(
        self, 
        documents: List[dict], 
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None,
    ) -> None:
        """Add documents with embeddings to ChromaDB."""
        if ids is None:
            ids = [doc.get("id", str(i)) for i, doc in enumerate(documents)]
        
        self.collection.add(
            embeddings=embeddings,
            documents=[doc.get("content", "") for doc in documents],
            metadatas=[{k: v for k, v in doc.items() if k != "content"} for doc in documents],
            ids=ids,
        )
    
    async def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[dict]:
        """Search for similar documents in ChromaDB."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
        )
        
        documents = []
        for i in range(len(results["ids"][0])):
            doc = {
                "id": results["ids"][0][i],
                "content": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            }
            documents.append(doc)
        
        return documents
    
    async def delete(self, ids: List[str]) -> None:
        """Delete documents from ChromaDB."""
        self.collection.delete(ids=ids)


class PineconeVectorStore(VectorStore):
    """Pinecone implementation for production."""
    
    def __init__(self):
        from pinecone import Pinecone
        
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
    
    async def add_documents(
        self, 
        documents: List[dict], 
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None,
    ) -> None:
        """Add documents with embeddings to Pinecone."""
        if ids is None:
            ids = [doc.get("id", str(i)) for i, doc in enumerate(documents)]
        
        vectors = [
            {
                "id": ids[i],
                "values": embeddings[i],
                "metadata": {
                    "content": documents[i].get("content", "")[:1000],  # Pinecone metadata limit
                    **{k: v for k, v in documents[i].items() if k != "content"},
                },
            }
            for i in range(len(documents))
        ]
        
        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
    
    async def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
    ) -> List[dict]:
        """Search for similar documents in Pinecone."""
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_metadata,
        )
        
        documents = []
        for match in results.matches:
            doc = {
                "id": match.id,
                "content": match.metadata.get("content", ""),
                "metadata": {k: v for k, v in match.metadata.items() if k != "content"},
                "score": match.score,
            }
            documents.append(doc)
        
        return documents
    
    async def delete(self, ids: List[str]) -> None:
        """Delete documents from Pinecone."""
        self.index.delete(ids=ids)


_vector_store_instance: VectorStore = None


def get_vector_store() -> VectorStore:
    """Factory function to get the appropriate vector store (singleton)."""
    global _vector_store_instance
    if _vector_store_instance is None:
        if settings.USE_CHROMA:
            _vector_store_instance = ChromaVectorStore()
        else:
            _vector_store_instance = PineconeVectorStore()
    return _vector_store_instance
