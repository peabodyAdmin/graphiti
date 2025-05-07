"""Document processing utilities for Graphiti MCP server."""

import asyncio
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

class DocumentChunker:
    """Split large documents into overlapping chunks for processing."""
    
    def __init__(
        self,
        max_chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ):
        """Initialize the document chunker.
        
        Args:
            max_chunk_size: Maximum characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        
    def chunk_document(self, text: str) -> List[Tuple[str, int]]:
        """Split document into chunks with position tracking.
        
        Args:
            text: Document text to split
            
        Returns:
            List of (chunk_text, start_position) tuples
        """
        chunks = []
        pos = 0
        
        while pos < len(text):
            # Find a good break point
            chunk_end = min(pos + self.max_chunk_size, len(text))
            
            # If not at end, try to break at sentence or paragraph
            if chunk_end < len(text):
                # Try to find paragraph break
                para_break = text.rfind('\n\n', pos, chunk_end)
                if para_break != -1 and para_break > pos:
                    chunk_end = para_break
                else:
                    # Try to find sentence break
                    sentence_break = text.rfind('. ', pos, chunk_end)
                    if sentence_break != -1 and sentence_break > pos:
                        chunk_end = sentence_break + 1
                    else:
                        # Fall back to word break
                        word_break = text.rfind(' ', pos, chunk_end)
                        if word_break != -1 and word_break > pos:
                            chunk_end = word_break
            
            # Extract chunk
            chunk = text[pos:chunk_end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append((chunk, pos))
            
            # Move position for next chunk, accounting for overlap
            pos = max(pos + 1, chunk_end - self.chunk_overlap)
            
        return chunks

class DocumentProcessor:
    """Process large documents by chunking and managing parallel processing."""
    
    def __init__(
        self,
        chunker: Optional[DocumentChunker] = None,
        max_parallel_chunks: int = 5,
        episode_timeout: int = 120,
    ):
        """Initialize the document processor.
        
        Args:
            chunker: DocumentChunker instance or None to use defaults
            max_parallel_chunks: Maximum chunks to process in parallel
            episode_timeout: Timeout in seconds for processing each chunk
        """
        self.chunker = chunker or DocumentChunker()
        self.max_parallel_chunks = max_parallel_chunks
        self.episode_timeout = episode_timeout
        
    async def process_document(
        self,
        name: str,
        text: str,
        process_chunk_func,
        group_id: Optional[str] = None,
    ) -> Tuple[int, List[dict]]:
        """Process a document by chunking and processing in parallel.
        
        Args:
            name: Base name for the document chunks
            text: Document text to process
            process_chunk_func: Async function to process each chunk
            group_id: Optional group ID for the chunks
            
        Returns:
            Tuple of (successful_chunks, failed_chunks)
            where failed_chunks is a list of dicts with 'chunk', 'position', and 'error'
        """
        chunks = self.chunker.chunk_document(text)
        successful = 0
        failed = []
        
        # Process chunks in batches to limit concurrency
        for i in range(0, len(chunks), self.max_parallel_chunks):
            batch = chunks[i:i + self.max_parallel_chunks]
            tasks = []
            
            # Create tasks for this batch
            for chunk_text, pos in batch:
                chunk_name = f"{name} [chunk {i+1}/{len(chunks)}]"
                
                task = asyncio.create_task(
                    self._process_chunk_with_timeout(
                        process_chunk_func=process_chunk_func,
                        chunk_text=chunk_text,
                        chunk_name=chunk_name,
                        position=pos,
                        group_id=group_id,
                    )
                )
                tasks.append(task)
            
            # Wait for all tasks in batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for (chunk_text, pos), result in zip(batch, results):
                if isinstance(result, Exception):
                    failed.append({
                        'chunk': chunk_text,
                        'position': pos,
                        'error': str(result)
                    })
                    logger.error(
                        f"Failed to process chunk at position {pos}",
                        extra={
                            'error': str(result),
                            'position': pos,
                            'chunk_length': len(chunk_text)
                        }
                    )
                else:
                    successful += 1
                    logger.info(
                        f"Successfully processed chunk",
                        extra={
                            'position': pos,
                            'chunk_length': len(chunk_text)
                        }
                    )
        
        return successful, failed
        
    async def _process_chunk_with_timeout(
        self,
        process_chunk_func,
        chunk_text: str,
        chunk_name: str,
        position: int,
        group_id: Optional[str],
    ):
        """Process a single chunk with timeout."""
        try:
            async with asyncio.timeout(self.episode_timeout):
                await process_chunk_func(
                    name=chunk_name,
                    text=chunk_text,
                    group_id=group_id
                )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Timeout processing chunk at position {position}"
            )