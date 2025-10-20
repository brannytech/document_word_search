"""Chat interface for RAG system"""

import streamlit as st
from pathlib import Path
import os
from typing import List

from core.rag_engine import RAGEngine
from utils.helpers import get_all_files
from config import Config


def initialize_rag_engine():
    """Initialize or get RAG engine from session state"""
    if 'rag_engine' not in st.session_state:
        with st.spinner("🚀 Initializing RAG system..."):
            settings = st.session_state.user_settings
            
            st.session_state.rag_engine = RAGEngine(
                model_name=getattr(settings, 'rag_model', 'llama3.2'),
                embedding_model="all-MiniLM-L6-v2",
                vector_db_path="vector_store"
            )
    
    return st.session_state.rag_engine


def render_chat_tab():
    """Render the RAG chat interface"""
    
    st.header("💬 Chat with Your Documents")
    st.markdown("Ask questions and get answers from your documents using AI")
    
    # Initialize RAG engine
    try:
        rag_engine = initialize_rag_engine()
    except Exception as e:
        st.error(f"❌ Error initializing RAG system: {e}")
        st.info("💡 Make sure Ollama is installed and running. Visit: https://ollama.com/download")
        return
    
    # Sidebar configuration
    with st.sidebar:
        st.subheader("🤖 RAG Configuration")
        
        # Check system status
        ready, message = rag_engine.is_ready()
        
        if ready:
            st.success(f"✅ {message}")
        else:
            st.warning(f"⚠️ {message}")
        
        st.markdown("---")
        
        # Model selection
        st.subheader("🎯 Model Settings")
        
        available_models = rag_engine.llm.list_models()
        
        if available_models:
            current_model = rag_engine.llm.model_name
            
            # Find current model in list or use first available
            try:
                current_index = available_models.index(current_model)
            except:
                current_index = 0
            
            selected_model = st.selectbox(
                "LLM Model:",
                options=available_models,
                index=current_index,
                help="Select the Ollama model to use"
            )
            
            if selected_model != current_model:
                if st.button("🔄 Switch Model", use_container_width=True):
                    with st.spinner(f"Switching to {selected_model}..."):
                        success = rag_engine.switch_model(selected_model)
                        if success:
                            st.success(f"✅ Switched to {selected_model}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to switch to {selected_model}")
        else:
            st.warning("No Ollama models found")
            st.markdown("**Install a model:**")
            st.code("ollama pull llama3.2")
            st.code("ollama pull mistral")
        
        st.markdown("---")
        
        # Document indexing
        st.subheader("📚 Document Indexing")
        
        stats = rag_engine.get_stats()
        vector_stats = stats['vector_store']
        
        col1, col2 = st.columns(2)
        col1.metric("Indexed Files", vector_stats['unique_files'])
        col2.metric("Total Chunks", vector_stats['total_chunks'])
        
        if vector_stats['unique_files'] > 0:
            st.metric("Index Size", f"{vector_stats['db_size_mb']:.1f} MB")
        
        # Index documents button
        if st.button("🔄 Index Documents", use_container_width=True, key='index_docs_btn'):
            st.session_state.show_indexing = True
        
        # Indexing interface
        if st.session_state.get('show_indexing', False):
            with st.expander("📁 Index Documents", expanded=True):
                index_dir = st.text_input(
                    "Directory to Index:",
                    value=st.session_state.get('selected_directory', './documents'),
                    key='rag_index_dir'
                )
                
                file_types = st.multiselect(
                    "File Types:",
                    options=['.pdf', '.docx', '.doc'],
                    default=['.pdf', '.docx', '.doc'],
                    key='rag_file_types'
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("▶️ Start Indexing", use_container_width=True, key='start_index_btn'):
                        if os.path.exists(index_dir):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            def update_progress(current, total, filename):
                                progress = current / total if total > 0 else 0
                                progress_bar.progress(progress)
                                status_text.text(f"{filename} ({current}/{total})")
                            
                            try:
                                indexed, total = rag_engine.index_documents(
                                    directory=index_dir,
                                    file_types=file_types,
                                    progress_callback=update_progress
                                )
                                
                                progress_bar.empty()
                                status_text.empty()
                                
                                st.success(f"✅ Indexed {indexed} new documents (Total: {total})")
                                st.session_state.show_indexing = False
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error indexing: {e}")
                        else:
                            st.error("Directory not found!")
                
                with col2:
                    if st.button("❌ Cancel", use_container_width=True, key='cancel_index_btn'):
                        st.session_state.show_indexing = False
                        st.rerun()
        
        st.markdown("---")
        
        # Conversation management
        st.subheader("💬 Conversation")
        
        conv_stats = stats['conversation']
        st.metric("Messages", conv_stats['total_messages'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True, key='clear_chat_btn'):
                rag_engine.clear_conversation()
                st.session_state.chat_messages = []
                st.success("✅ Chat cleared!")
                st.rerun()
        
        with col2:
            if st.button("💾 Export Chat", use_container_width=True, key='export_chat_btn'):
                if conv_stats['total_messages'] > 0:
                    filepath = rag_engine.export_conversation()
                    if filepath:
                        st.success(f"✅ Exported to:\n{filepath}")
                        
                        # Offer download
                        with open(filepath, 'r') as f:
                            st.download_button(
                                label="📥 Download",
                                data=f.read(),
                                file_name=Path(filepath).name,
                                mime="application/json",
                                key='download_conv_btn',
                                use_container_width=True
                            )
                else:
                    st.warning("No messages to export")
    
    # Main chat area
    if not ready:
        st.info("👆 Please index documents in the sidebar to get started")
        return
    
    # Initialize chat messages in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Display chat history
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.chat_messages:
            with st.chat_message(message['role']):
                st.markdown(message['content'])
                
                # Show citations if available
                if message.get('citations'):
                    with st.expander(f"📎 Sources ({len(message['citations'])})"):
                        for i, citation in enumerate(message['citations'], 1):
                            st.markdown(
                                f"**{i}. {citation['file_name']}** (Page {citation['page_number']})\n\n"
                                f"_{citation['chunk']}_"
                            )
                            st.markdown("---")
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message to chat
        st.session_state.chat_messages.append({
            'role': 'user',
            'content': prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Check if streaming is enabled
            stream_responses = True  # Default to streaming
            
            if stream_responses:
                # Streaming response
                full_response = ""
                
                with st.spinner("🤔 Thinking..."):
                    result = rag_engine.answer_question(
                        question=prompt,
                        stream=True
                    )
                
                # Stream the response
                for chunk in result['answer']:
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
                # Show citations
                if result['citations']:
                    with st.expander(f"📎 Sources ({len(result['citations'])})"):
                        for i, citation in enumerate(result['citations'], 1):
                            st.markdown(
                                f"**{i}. {citation['file_name']}** (Page {citation.get('page_number', 'N/A')})\n\n"
                                f"_{citation['chunk']}_"
                            )
                            st.markdown("---")
                
                # Add assistant message to chat
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': full_response,
                    'citations': result['citations']
                })
                
            else:
                # Non-streaming response
                with st.spinner("🤔 Thinking..."):
                    result = rag_engine.answer_question(
                        question=prompt,
                        stream=False
                    )
                
                message_placeholder.markdown(result['answer'])
                
                # Show citations
                if result['citations']:
                    with st.expander(f"📎 Sources ({len(result['citations'])})"):
                        for i, citation in enumerate(result['citations'], 1):
                            st.markdown(
                                f"**{i}. {citation['file_name']}** (Page {citation.get('page_number', 'N/A')})\n\n"
                                f"_{citation['chunk']}_"
                            )
                            st.markdown("---")
                
                # Add assistant message to chat
                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': result['answer'],
                    'citations': result['citations']
                })
    
    # Tips section at bottom
    if len(st.session_state.chat_messages) == 0:
        st.markdown("---")
        st.markdown("### 💡 Tips:")
        st.markdown("""
        - **Ask specific questions** about your documents
        - **Follow-up questions** are supported - the AI remembers context
        - **Multi-document reasoning** - ask questions that span multiple files
        - **Citations** are automatically included in answers
        - **Index new documents** using the sidebar when you add files
        """)