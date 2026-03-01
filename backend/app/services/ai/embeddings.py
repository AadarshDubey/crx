from typing import List, Optional
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    """
    Generate embeddings for semantic search and RAG.
    
    Uses local sentence-transformers model (free, no API needed).
    """
    
    def __init__(self):
        # Use a small, fast model - runs locally, no API key needed
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimensions = 384  # all-MiniLM-L6-v2 dimension
    
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or len(text.strip()) == 0:
            return [0.0] * self.dimensions
        
        # Truncate to model's max context
        text = text[:512]
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
            
        except Exception as e:
            raise Exception(f"Embedding generation failed: {e}")
    
    async def embed_batch(
        self, 
        texts: List[str], 
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embedding vectors
        """
        # Clean and truncate
        texts = [t[:512] if t else "" for t in texts]
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True, batch_size=batch_size)
            return embeddings.tolist()
        except Exception as e:
            # Fill with zero vectors on error
            return [[0.0] * self.dimensions] * len(texts)
    
    async def embed_for_search(self, query: str) -> List[float]:
        """
        Generate embedding optimized for search queries.
        """
        return await self.embed(query)
    
    async def embed_for_storage(self, document: str) -> List[float]:
        """
        Generate embedding optimized for document storage.
        """
        return await self.embed(document)


# Singleton instance
embedding_service = EmbeddingService()
