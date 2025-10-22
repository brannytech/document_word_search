"""Manage conversation history and context"""

from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path


@dataclass
class Message:
    """Single conversation message"""
    role: str  # 'user' or 'assistant'
    content: str
    citations: Optional[List[Dict]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class ConversationManager:
    """Manage conversation history for RAG chat"""
    
    def __init__(self, max_history: int = 50):
        """
        Initialize conversation manager
        
        Args:
            max_history: Maximum number of messages to keep
        """
        self.max_history = max_history
        self.messages: List[Message] = []
        self.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"[ConversationManager] Initialized with conversation ID: {self.conversation_id}")
    
    def add_message(self, role: str, content: str, citations: Optional[List[Dict]] = None):
        """
        Add message to conversation
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            citations: Optional list of citations
        """
        message = Message(
            role=role,
            content=content,
            citations=citations
        )
        
        self.messages.append(message)
        
        # Trim if exceeds max history
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
        
        print(f"[ConversationManager] Added {role} message. Total messages: {len(self.messages)}")
    
    def get_history(self, max_messages: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history
        
        Args:
            max_messages: Maximum number of recent messages to return
            
        Returns:
            List of message dictionaries
        """
        messages = self.messages if max_messages is None else self.messages[-max_messages:]
        return [msg.to_dict() for msg in messages]
    
    def get_context_history(self, max_pairs: int = 5) -> List[Dict]:
        """
        Get recent conversation for LLM context (question-answer pairs)
        
        Args:
            max_pairs: Maximum number of Q&A pairs to include
            
        Returns:
            List of recent messages formatted for LLM
        """
        # Get last N*2 messages (pairs of user/assistant)
        recent = self.messages[-(max_pairs * 2):]
        
        # Format for LLM context (exclude citations for brevity)
        formatted = []
        for msg in recent:
            formatted.append({
                'role': msg.role,
                'content': msg.content
            })
        
        return formatted
    
    def clear_history(self):
        """Clear all conversation history"""
        self.messages = []
        self.conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"[ConversationManager] Cleared history. New conversation ID: {self.conversation_id}")
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message"""
        for msg in reversed(self.messages):
            if msg.role == 'user':
                return msg.content
        return None
    
    def get_last_assistant_message(self) -> Optional[Dict]:
        """Get the last assistant message with citations"""
        for msg in reversed(self.messages):
            if msg.role == 'assistant':
                return msg.to_dict()
        return None
    
    def export_conversation(self, output_dir: str = "conversations") -> str:
        """
        Export conversation to JSON file
        
        Args:
            output_dir: Directory to save conversation
            
        Returns:
            Path to saved file
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            filename = f"conversation_{self.conversation_id}.json"
            filepath = output_path / filename
            
            conversation_data = {
                'conversation_id': self.conversation_id,
                'created_at': self.messages[0].timestamp if self.messages else datetime.now().isoformat(),
                'message_count': len(self.messages),
                'messages': [msg.to_dict() for msg in self.messages]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            print(f"[ConversationManager] Exported conversation to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"[ConversationManager] Error exporting conversation: {e}")
            return ""
    
    def get_stats(self) -> Dict:
        """Get conversation statistics"""
        user_messages = sum(1 for msg in self.messages if msg.role == 'user')
        assistant_messages = sum(1 for msg in self.messages if msg.role == 'assistant')
        
        total_citations = sum(
            len(msg.citations) if msg.citations else 0 
            for msg in self.messages if msg.role == 'assistant'
        )
        
        return {
            'total_messages': len(self.messages),
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'total_citations': total_citations,
            'conversation_id': self.conversation_id
        }
    
    def format_for_display(self) -> List[Dict]:
        """Format conversation for UI display"""
        formatted = []
        
        for msg in self.messages:
            display_msg = {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp,
                'citations': []
            }
            
            # Format citations for display
            if msg.citations:
                for citation in msg.citations:
                    display_msg['citations'].append({
                        'file_name': citation.get('file_name', 'Unknown'),
                        'page': citation.get('page_number', 'N/A'),
                        'excerpt': citation.get('chunk', citation.get('context', ''))[:200] + '...'
                    })
            
            formatted.append(display_msg)
        
        return formatted