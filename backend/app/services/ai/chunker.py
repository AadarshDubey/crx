"""
Content Chunking Service

Implements sliding-window chunking for news articles to maximize
semantic coverage in the vector store. Tweets are not chunked
(they are already short enough to embed whole).

Strategy:
  - Tweets: 1 document -> 1 vector (whole text)
  - News articles: 1 document -> N overlapping chunks
      chunk_size=380 chars, overlap=80 chars
      Each chunk stores parent_id + chunk_index in metadata
      so retrieval can de-duplicate back to source articles.
"""

from typing import List
from dataclasses import dataclass


@dataclass
class Chunk:
    """A single chunk ready for embedding and vector storage."""
    chunk_id: str        # unique ID: f"{parent_id}_chunk_{index}"
    parent_id: str       # original article/tweet ID
    text: str            # the actual text to embed
    chunk_index: int     # 0-based position in the chunk list
    total_chunks: int    # how many chunks the parent was split into
    metadata: dict       # all metadata to store alongside the vector


class ContentChunker:
    """
    Sliding-window text chunker optimised for sentence-transformers.

    The all-MiniLM-L6-v2 model has a 512 WordPiece-token limit.
    ~380 chars gives safe headroom while keeping semantically coherent windows.
    Overlap (80 chars) lets adjacent chunks share context at boundaries.
    """

    TWEET_CHUNK_SIZE = 500      # tweets always fit whole
    NEWS_CHUNK_SIZE = 380       # chars per chunk for articles
    NEWS_CHUNK_OVERLAP = 80     # chars of overlap between consecutive chunks

    def chunk_tweet(self, tweet_id: str, text: str, metadata: dict) -> List[Chunk]:
        """Tweets are short -- store them as a single chunk."""
        clean = self._clean(text)
        if not clean:
            return []

        return [Chunk(
            chunk_id=tweet_id,
            parent_id=tweet_id,
            text=clean[:self.TWEET_CHUNK_SIZE],
            chunk_index=0,
            total_chunks=1,
            metadata={**metadata, "chunk_index": 0, "total_chunks": 1},
        )]

    def chunk_article(
        self,
        article_id: str,
        title: str,
        content: str,
        metadata: dict,
    ) -> List[Chunk]:
        """
        Chunk a news article using a sliding window.

        The title is prepended to EVERY chunk so the embedding always
        knows which article the text belongs to.
        """
        clean_content = self._clean(content)
        clean_title = self._clean(title)

        if not clean_content:
            if clean_title:
                return [Chunk(
                    chunk_id=f"{article_id}_chunk_0",
                    parent_id=article_id,
                    text=clean_title,
                    chunk_index=0,
                    total_chunks=1,
                    metadata={**metadata, "chunk_index": 0, "total_chunks": 1, "is_title_only": True},
                )]
            return []

        windows = self._sliding_windows(clean_content)
        total = len(windows)

        chunks = []
        for idx, window in enumerate(windows):
            title_prefix = f"Title: {clean_title[:80]}\n\n" if clean_title else ""
            text = (title_prefix + window)[:self.NEWS_CHUNK_SIZE + len(title_prefix)]

            chunks.append(Chunk(
                chunk_id=f"{article_id}_chunk_{idx}",
                parent_id=article_id,
                text=text,
                chunk_index=idx,
                total_chunks=total,
                metadata={
                    **metadata,
                    "chunk_index": idx,
                    "total_chunks": total,
                    "parent_id": article_id,
                    "is_title_only": False,
                },
            ))

        return chunks

    def _sliding_windows(self, text: str) -> List[str]:
        """
        Split text into overlapping windows, preferring sentence boundaries.
        """
        size = self.NEWS_CHUNK_SIZE
        overlap = self.NEWS_CHUNK_OVERLAP

        if len(text) <= size:
            return [text]

        windows = []
        start = 0

        while start < len(text):
            end = start + size

            if end < len(text):
                # Try to find a sentence boundary in last 60 chars of window
                search_zone = text[max(start, end - 60): end]
                best_break = -1
                for sep in ('. ', '! ', '? ', '\n'):
                    pos = search_zone.rfind(sep)
                    if pos != -1:
                        best_break = max(start, end - 60) + pos + len(sep)
                        break

                if best_break != -1:
                    end = best_break

            window = text[start:end].strip()
            if window:
                windows.append(window)

            if end >= len(text):
                break

            start = max(start + 1, end - overlap)

        return windows

    def _clean(self, text: str) -> str:
        """Normalize whitespace."""
        if not text:
            return ""
        return " ".join(text.split()).strip()


# Singleton
content_chunker = ContentChunker()
