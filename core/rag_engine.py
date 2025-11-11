"""Main RAG orchestration engine with LAZY LOADING to prevent app slowdown"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import re

from core.vector_store import DocumentVectorStore
from core.llm_client import OllamaClient
from core.conversation_manager import ConversationManager
from core.prompt_templates import build_simple_prompt, build_followup_prompt, build_multi_doc_prompt
from core.text_extractor import TextExtractor
from utils.helpers import get_all_files
from config import Config


class RAGEngine:
    """Main RAG engine orchestrating retrieval and generation"""
    
    def __init__(self, model_name: str = "llama3.2:latest", 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 vector_db_path: str = "vector_store"):
        """
        Initialize RAG engine
        
        Args:
            model_name: Ollama model name
            embedding_model: Sentence transformer model
            vector_db_path: Path to vector database
        """
        print("[RAGEngine] Initializing RAG system...")
        
        try:
            # Initialize vector store (downloads embedding model if needed)
            print("[RAGEngine] Loading vector store...")
            self.vector_store = DocumentVectorStore(
                persist_directory=vector_db_path,
                embedding_model=embedding_model
            )
            print("[RAGEngine] ✅ Vector store ready")
            
            # Initialize LLM client
            print("[RAGEngine] Connecting to Ollama...")
            self.llm = OllamaClient(model_name=model_name)
            print("[RAGEngine] ✅ LLM client ready")
            
            # Initialize conversation manager
            self.conversation = ConversationManager(max_history=50)
            print("[RAGEngine] ✅ Conversation manager ready")
            
            # Settings
            self.top_k = 10
            self.chunk_size = 500
            self.chunk_overlap = 50
            
            print("[RAGEngine] 🎉 Initialization complete!")
            print(f"[RAGEngine] LLM Available: {self.llm.is_available()}")
            
        except Exception as e:
            print(f"[RAGEngine] ❌ Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def is_ready(self) -> Tuple[bool, str]:
        """
        Check if RAG system is ready
        
        Returns:
            (ready, message)
        """
        if not self.llm.is_available():
            return False, "Ollama not available. Please install Ollama and pull a model."
        
        stats = self.vector_store.get_stats()
        if stats['unique_files'] == 0:
            return False, "No documents indexed. Please index documents first."
        
        return True, "RAG system ready!"
    
    def index_documents(self, directory: str, file_types: List[str] = None,
                       progress_callback=None) -> Tuple[int, int]:
        """
        Index documents for RAG
        
        Args:
            directory: Directory containing documents
            file_types: File extensions to index
            progress_callback: Callback for progress updates
            
        Returns:
            (indexed_count, total_count)
        """
        if file_types is None:
            file_types = Config.SUPPORTED_EXTENSIONS
        
        print(f"[RAGEngine] Starting document indexing from {directory}")
        
        # Get all files
        files = get_all_files(directory, file_types)
        total_files = len(files)
        
        if total_files == 0:
            print("[RAGEngine] No files found to index")
            return 0, 0
        
        print(f"[RAGEngine] Found {total_files} files to process")
        
        # Filter to only new/changed files
        files_to_index = [
            f for f in files 
            if not self.vector_store.is_indexed(str(f))
        ]
        
        if not files_to_index:
            print("[RAGEngine] All files already indexed")
            return 0, total_files
        
        print(f"[RAGEngine] {len(files_to_index)} files need indexing")
        
        # Extract text using existing extractor
        extractor = TextExtractor(max_workers=Config.MAX_WORKERS)
        
        def update_progress(current, total, filename):
            if progress_callback:
                progress_callback(current, total, f"Extracting: {filename}")
        
        extracted_texts = extractor.extract_all(files_to_index, update_progress)
        
        print(f"[RAGEngine] Extracted text from {len(extracted_texts)} files")
        
        # Index each document
        indexed_count = 0
        for i, (file_path, text) in enumerate(extracted_texts.items(), 1):
            if progress_callback:
                progress_callback(i, len(extracted_texts), f"Indexing: {Path(file_path).name}")
            
            try:
                self.vector_store.add_document(
                    file_path=file_path,
                    text=text,
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                )
                indexed_count += 1
            except Exception as e:
                print(f"[RAGEngine] Error indexing {file_path}: {e}")
        
        print(f"[RAGEngine] ✅ Successfully indexed {indexed_count}/{len(files_to_index)} files")
        
        return indexed_count, total_files
    
    def answer_question(self, question: str, stream: bool = True) -> Dict:
        """
        Answer question using RAG
        
        Args:
            question: User question
            stream: Whether to stream response
            
        Returns:
            Dict with answer, contexts, and citations
        """
        print(f"[RAGEngine] Processing question: {question[:100]}...")
        
        # Check if ready
        ready, message = self.is_ready()
        if not ready:
            return {
                'answer': f"Error: {message}",
                'contexts': [],
                'citations': [],
                'stream': False
            }
        
        # Retrieve relevant contexts
        contexts = self.semantic_retrieve(question, self.top_k)
        
        if not contexts:
            return {
                'answer': "I couldn't find any relevant information in the documents to answer your question.",
                'contexts': [],
                'citations': [],
                'stream': False
            }
        
        print(f"[RAGEngine] Retrieved {len(contexts)} relevant contexts")
        
        # Determine prompt type
        conversation_history = self.conversation.get_context_history(max_pairs=3)
        is_follow_up = len(conversation_history) > 0
        
        # Build appropriate prompt
        if is_follow_up:
            prompt = build_followup_prompt(question, contexts, conversation_history)
        elif len(set(c['file_path'] for c in contexts)) > 1:
            prompt = build_multi_doc_prompt(question, contexts)
        else:
            prompt = build_simple_prompt(question, contexts)
        
        # Generate answer
        if stream:
            # Return generator for streaming
            return {
                'answer': self.llm.stream_generate(prompt),
                'contexts': contexts,
                'citations': contexts[:5],  # Top 5 as citations
                'stream': True
            }
        else:
            answer = self.llm.generate(prompt, stream=False)
            
            # Extract citations from contexts
            citations = self._extract_citations(answer, contexts)
            
            # Add to conversation
            self.conversation.add_message('user', question)
            self.conversation.add_message('assistant', answer, citations)
            
            return {
                'answer': answer,
                'contexts': contexts,
                'citations': citations,
                'stream': False
            }
    
    def semantic_retrieve(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Semantic retrieval using vector store
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of context dictionaries
        """
        print(f"[RAGEngine] Semantic retrieval for: {query[:50]}...")
        
        # Semantic search (vector store)
        semantic_results = self.vector_store.semantic_search(
            query=query,
            top_k=top_k
        )
        
        print(f"[RAGEngine] Retrieved {len(semantic_results)} results")
        
        return semantic_results
    
    def _extract_citations(self, answer: str, contexts: List[Dict]) -> List[Dict]:
        """Extract citations mentioned in answer"""
        citations = []
        
        # Look for citation patterns: [Source: filename, Page X]
        citation_pattern = r'\[Source:\s*([^,]+),\s*Page\s*(\d+)\]'
        
        matches = re.findall(citation_pattern, answer)
        
        if matches:
            # Match found citations to contexts
            for filename, page in matches:
                for ctx in contexts:
                    if filename.strip() in ctx['file_name']:
                        citations.append({
                            'file_name': ctx['file_name'],
                            'file_path': ctx['file_path'],
                            'page_number': int(page),
                            'chunk': ctx['chunk'][:200] + '...'
                        })
                        break
        else:
            # No explicit citations, return top contexts
            for ctx in contexts[:5]:
                citations.append({
                    'file_name': ctx['file_name'],
                    'file_path': ctx['file_path'],
                    'page_number': ctx['page_number'],
                    'chunk': ctx['chunk'][:200] + '...'
                })
        
        return citations
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation.clear_history()
        print("[RAGEngine] Conversation cleared")
    
    def export_conversation(self) -> str:
        """Export conversation to file"""
        return self.conversation.export_conversation()
    
    def get_stats(self) -> Dict:
        """Get RAG system statistics"""
        vector_stats = self.vector_store.get_stats()
        conversation_stats = self.conversation.get_stats()
        
        return {
            'vector_store': vector_stats,
            'conversation': conversation_stats,
            'llm_available': self.llm.is_available(),
            'llm_model': self.llm.model_name
        }
    
    def switch_model(self, model_name: str) -> bool:
        """Switch LLM model"""
        return self.llm.set_model(model_name)
    

    