"""Vector store using ChromaDB for semantic search - 100% FREE"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import hashlib
from datetime import datetime
import threading


class DocumentVectorStore:
    """ChromaDB-based vector store for semantic document search"""
    
    def __init__(self, persist_directory: str = "vector_store", 
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize vector store with ChromaDB
        
        Args:
            persist_directory: Directory to store vector database
            embedding_model: Sentence transformer model name
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        
        print(f"[VectorStore] Initializing ChromaDB at {persist_directory}")
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Load embedding model
        print(f"[VectorStore] Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # Get or create collection
        self.collection_name = "documents"
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            print(f"[VectorStore] Loaded existing collection with {self.collection.count()} documents")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"[VectorStore] Created new collection")
        
        self.lock = threading.Lock()
        self.stop_requested = False
    
    def _compute_chunk_id(self, file_path: str, chunk_index: int) -> str:
        """Generate unique ID for document chunk"""
        key = f"{file_path}_{chunk_index}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute hash based on file metadata"""
        path = Path(file_path)
        if not path.exists():
            return ""
        
        stat = path.stat()
        hash_string = f"{file_path}|{stat.st_size}|{stat.st_mtime}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def is_indexed(self, file_path: str) -> bool:
        """Check if file is already indexed"""
        try:
            file_hash = self._compute_file_hash(file_path)
            if not file_hash:
                return False
            
            # Query for any chunks from this file
            results = self.collection.get(
                where={"file_path": file_path},
                limit=1
            )
            
            if not results['ids']:
                return False
            
            # Check if file hash matches (file unchanged)
            if results['metadatas']:
                stored_hash = results['metadatas'][0].get('file_hash', '')
                return stored_hash == file_hash
            
            return False
        except Exception as e:
            print(f"[VectorStore] Error checking if indexed: {e}")
            return False
    
    def add_document(self, file_path: str, text: str, 
                    chunk_size: int = 500, chunk_overlap: int = 50,
                    metadata: Dict = None):
        """
        Add document to vector store with chunking
        
        Args:
            file_path: Path to document
            text: Extracted text content
            chunk_size: Size of text chunks (characters)
            chunk_overlap: Overlap between chunks
            metadata: Additional metadata
        """
        if not text or not text.strip():
            print(f"[VectorStore] Skipping empty document: {file_path}")
            return
        
        with self.lock:
            try:
                # Remove existing chunks for this file
                self._remove_document_chunks(file_path)
                
                # Split text into chunks
                chunks = self._create_chunks(text, chunk_size, chunk_overlap)
                
                if not chunks:
                    print(f"[VectorStore] No chunks created for: {file_path}")
                    return
                
                # Prepare data for batch insert
                chunk_ids = []
                embeddings = []
                documents = []
                metadatas = []
                
                file_hash = self._compute_file_hash(file_path)
                file_name = Path(file_path).name
                
                print(f"[VectorStore] Creating {len(chunks)} chunks for {file_name}")
                
                for i, chunk in enumerate(chunks):
                    if self.stop_requested:
                        break
                    
                    chunk_id = self._compute_chunk_id(file_path, i)
                    chunk_ids.append(chunk_id)
                    documents.append(chunk)
                    
                    # Create metadata
                    chunk_metadata = {
                        'file_path': file_path,
                        'file_name': file_name,
                        'file_hash': file_hash,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'indexed_at': datetime.now().isoformat()
                    }
                    
                    if metadata:
                        chunk_metadata.update(metadata)
                    
                    metadatas.append(chunk_metadata)
                
                if self.stop_requested:
                    return
                
                # Generate embeddings in batch
                print(f"[VectorStore] Generating embeddings for {len(chunks)} chunks...")
                embeddings = self.embedding_model.encode(
                    documents,
                    show_progress_bar=False,
                    convert_to_numpy=True
                ).tolist()
                
                # Add to collection
                self.collection.add(
                    ids=chunk_ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                
                print(f"[VectorStore] ✅ Indexed {len(chunks)} chunks from {file_name}")
                
            except Exception as e:
                print(f"[VectorStore] Error adding document {file_path}: {e}")
                import traceback
                traceback.print_exc()
    
    def _create_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        text = text.strip()
        
        if len(text) <= chunk_size:
            return [text]
        
        start = 0
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings near the boundary
                boundary_search = text[end-100:end+100] if end+100 < len(text) else text[end-100:]
                sentence_ends = [i for i, c in enumerate(boundary_search) if c in '.!?']
                
                if sentence_ends:
                    # Use the last sentence ending before or closest to the boundary
                    closest_end = sentence_ends[-1] if sentence_ends[-1] < 100 else sentence_ends[0]
                    end = (end - 100) + closest_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap
            
            # Safety: prevent infinite loop
            if start <= 0:
                start = end
        
        return chunks
    
    def semantic_search(self, query: str, top_k: int = 10, 
                       file_filter: Optional[List[str]] = None) -> List[Dict]:
        """
        Perform semantic search using embeddings
        
        Args:
            query: Search query
            top_k: Number of results to return
            file_filter: Optional list of file paths to restrict search
            
        Returns:
            List of dicts with keys: file_path, file_name, chunk, score, page_number
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                query,
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()
            
            # Build where filter if files specified
            where = None
            if file_filter:
                where = {"file_path": {"$in": file_filter}}
            
            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, 100),  # Safety limit
                where=where,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    chunk_index = results['metadatas'][0][i]['chunk_index']
                    # Estimate page number from chunk index
                    page_number = (chunk_index * 500) // 3000 + 1  # Rough estimate
                    
                    formatted_results.append({
                        'file_path': results['metadatas'][0][i]['file_path'],
                        'file_name': results['metadatas'][0][i]['file_name'],
                        'chunk': results['documents'][0][i],
                        'chunk_index': chunk_index,
                        'page_number': page_number,
                        'score': 1.0 - results['distances'][0][i],  # Convert distance to similarity
                        'metadata': results['metadatas'][0][i]
                    })
            
            print(f"[VectorStore] Semantic search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            print(f"[VectorStore] Error in semantic search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _remove_document_chunks(self, file_path: str):
        """Remove all chunks for a document"""
        try:
            # Get all chunk IDs for this file
            results = self.collection.get(
                where={"file_path": file_path}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"[VectorStore] Removed {len(results['ids'])} existing chunks for {Path(file_path).name}")
        except Exception as e:
            print(f"[VectorStore] Error removing document chunks: {e}")
    
    def get_stats(self) -> Dict:
        """Get vector store statistics"""
        try:
            count = self.collection.count()
            
            # Get unique files
            all_metadata = self.collection.get(include=['metadatas'])
            unique_files = set()
            if all_metadata['metadatas']:
                unique_files = {m['file_path'] for m in all_metadata['metadatas']}
            
            # Estimate size
            db_size = sum(f.stat().st_size for f in self.persist_directory.rglob('*') if f.is_file())
            
            return {
                'total_chunks': count,
                'unique_files': len(unique_files),
                'db_size_mb': db_size / (1024 * 1024),
                'embedding_dim': self.embedding_dim
            }
        except Exception as e:
            print(f"[VectorStore] Error getting stats: {e}")
            return {'total_chunks': 0, 'unique_files': 0, 'db_size_mb': 0}
    
    def clear_index(self):
        """Clear all indexed documents"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print("[VectorStore] Index cleared")
        except Exception as e:
            print(f"[VectorStore] Error clearing index: {e}")
    
    def stop(self):
        """Stop all operations"""
        self.stop_requested = True