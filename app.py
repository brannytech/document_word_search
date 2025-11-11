"""Streamlit application with Hybrid Search System - ALL BUGS FIXED"""

import streamlit as st
import pandas as pd
from pathlib import Path
import os
from typing import List, Tuple
import psutil

# from datetime import datetime  # Removed unused import
# import reportlab  --- IGNORE ---



#"""
#Phase 1(b): Export All Results to Single Document

#Add this to app.py after the imports
#"""

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
# import PyPDF2  # Removed unused import
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

from core.hybrid_search_engine import HybridSearchEngine
from core.document_index import DocumentIndex
from core.result_processor import ResultProcessor
from core.highlighter import DocumentHighlighter
from core.search_manager import SearchManager
from core.settings_manager import SettingsManager
from core.cache_manager import TextCache
# from core.text_extractor import TextExtractor  # Removed unused import
from config import Config
from utils.helpers import get_file_size, get_all_files


# Import for RAG TAB
#from core.vector_store import DocumentVectorStore
#from core.llm_client import OllamaClient
#from core.rag_engine import RAGEngine
#from core.conversation_manager import ConversationManager



def export_combined_results_to_docx(results, keyword, output_path):
    """
    Export all search results to a single DOCX file with proper formatting
    
    Args:
        results: Dictionary of search results {file_path: [SearchResult, ...]}
        keyword: Search keyword used
        output_path: Path to save the output file
    
    Returns:
        Path to the created file
    """
    doc = Document()
    
    # Add title
    title = doc.add_heading(f'Search Results for: "{keyword}"', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add metadata
    doc.add_paragraph(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    doc.add_paragraph(f'Total files with matches: {len(results)}')
    doc.add_paragraph(f'Total matches: {sum(len(r) for r in results.values())}')
    doc.add_paragraph('')
    
    # Add horizontal line
    doc.add_paragraph('_' * 80)
    doc.add_paragraph('')
    
    # Process each file
    for file_path, matches in results.items():
        file_name = Path(file_path).name
        
        # File header
        file_heading = doc.add_heading(f'📄 {file_name}', level=1)
        file_heading_format = file_heading.runs[0]
        file_heading_format.font.color.rgb = RGBColor(0, 102, 204)
        
        doc.add_paragraph(f'File: {file_path}')
        doc.add_paragraph(f'Matches found: {len(matches)}')
        doc.add_paragraph('')
        
        # Group matches by page
        matches_by_page = {}
        for match in matches:
            page = match.page_number
            if page not in matches_by_page:
                matches_by_page[page] = []
            matches_by_page[page].append(match)
        
        # Add matches page by page
        for page_num in sorted(matches_by_page.keys()):
            page_matches = matches_by_page[page_num]
            
            # Page subheading
            doc.add_heading(f'Page {page_num}', level=2)
            
            # Add each match
            for i, match in enumerate(page_matches, 1):
                # Create paragraph with the context
                p = doc.add_paragraph()
                
                # Add match number
                run = p.add_run(f'[Match {i}] ')
                run.bold = True
                run.font.color.rgb = RGBColor(102, 102, 102)
                
                # Add context with citation
                context_text = match.context.strip()
                p.add_run(context_text)
                
                # Add page citation at the end (smaller, superscript-style)
                citation_run = p.add_run(f' (page {page_num})')
                citation_run.font.size = Pt(9)
                citation_run.font.color.rgb = RGBColor(128, 128, 128)
                citation_run.italic = True
                
                # Add spacing
                doc.add_paragraph('')
            
            # Separator between pages
            doc.add_paragraph('─' * 60)
            doc.add_paragraph('')
        
        # File separator
        doc.add_paragraph('')
        doc.add_paragraph('═' * 80)
        doc.add_paragraph('')
    
    # Save document
    doc.save(output_path)
    return output_path


def export_combined_results_to_pdf(results, keyword, output_path):
    """
    Export all search results to a single PDF file with proper formatting
    
    Args:
        results: Dictionary of search results {file_path: [SearchResult, ...]}
        keyword: Search keyword used
        output_path: Path to save the output file
    
    Returns:
        Path to the created file
    """
    from datetime import datetime
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#0066CC',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    file_heading_style = ParagraphStyle(
        'FileHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='#0066CC',
        spaceAfter=12,
        spaceBefore=12
    )
    
    page_heading_style = ParagraphStyle(
        'PageHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#333333',
        spaceAfter=8,
        spaceBefore=8
    )
    
    context_style = ParagraphStyle(
        'Context',
        parent=styles['BodyText'],
        fontSize=11,
        leading=14,
        spaceAfter=10,
        alignment=TA_JUSTIFY
    )
    
    # citation_style = ParagraphStyle(
    #     'Citation',
    #     parent=styles['BodyText'],
    #     fontSize=9,
    #     textColor='#808080',
    #     italic=True
    # )
    
    # Add title
    elements.append(Paragraph(f'Search Results for: "{keyword}"', title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Add metadata
    metadata_text = f"""
    Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br/>
    Total files with matches: {len(results)}<br/>
    Total matches: {sum(len(r) for r in results.values())}
    """
    elements.append(Paragraph(metadata_text, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Process each file
    for file_idx, (file_path, matches) in enumerate(results.items()):
        file_name = Path(file_path).name
        
        # File header
        elements.append(Paragraph(f'📄 {file_name}', file_heading_style))
        elements.append(Paragraph(f'File: {file_path}', styles['Normal']))
        elements.append(Paragraph(f'Matches found: {len(matches)}', styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Group matches by page
        matches_by_page = {}
        for match in matches:
            page = match.page_number
            if page not in matches_by_page:
                matches_by_page[page] = []
            matches_by_page[page].append(match)
        
        # Add matches page by page
        for page_num in sorted(matches_by_page.keys()):
            page_matches = matches_by_page[page_num]
            
            # Page subheading
            elements.append(Paragraph(f'Page {page_num}', page_heading_style))
            
            # Add each match
            for i, match in enumerate(page_matches, 1):
                context_text = match.context.strip().replace('<', '&lt;').replace('>', '&gt;')
                
                match_text = f'<b>[Match {i}]</b> {context_text} <i><font size="9" color="#808080">(page {page_num})</font></i>'
                elements.append(Paragraph(match_text, context_style))
            
            elements.append(Spacer(1, 0.15*inch))
        
        # File separator
        if file_idx < len(results) - 1:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(PageBreak())
    
    # Build PDF
    doc.build(elements)
    return output_path


# Page configuration
st.set_page_config(
    page_title=Config.PAGE_TITLE,
    page_icon=Config.PAGE_ICON,
    layout=Config.LAYOUT
)

# Initialize session state
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'highlighted_files' not in st.session_state:
    st.session_state.highlighted_files = None
if 'searching' not in st.session_state:
    st.session_state.searching = False
if 'search_manager' not in st.session_state:
    st.session_state.search_manager = None
if 'search_engine' not in st.session_state:
    st.session_state.search_engine = None
if 'processed_results' not in st.session_state:
    st.session_state.processed_results = None
if 'search_stopped' not in st.session_state:
    st.session_state.search_stopped = False
if 'completion_stats' not in st.session_state:
    st.session_state.completion_stats = (0, 0)
if 'user_settings' not in st.session_state:
    st.session_state.user_settings = SettingsManager.load_settings()
if 'text_cache' not in st.session_state:
    settings = st.session_state.user_settings
    st.session_state.text_cache = TextCache(
        max_size_mb=settings.cache.max_size_mb,
        persistent=settings.cache.persistent
    ) if settings.cache.enabled else None
if 'extracted_texts' not in st.session_state:
    st.session_state.extracted_texts = {}
if 'settings_changed' not in st.session_state:
    st.session_state.settings_changed = False
if 'prevent_rerun' not in st.session_state:
    st.session_state.prevent_rerun = False
if 'selected_directory' not in st.session_state:
    st.session_state.selected_directory = "./documents"
if 'folder_picker_clicked' not in st.session_state:
    st.session_state.folder_picker_clicked = False


# RAG Engine Initialization
if 'rag_initialized' not in st.session_state:
    st.session_state.rag_initialized = False

if 'rag_engine' not in st.session_state:
    st.session_state.rag_engine = None

if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []



def build_highlighted_html(context: str, match_positions: List[Tuple[int, int]]) -> str:
    """Build HTML with all matches highlighted in yellow"""
    if not match_positions:
        return f'<span style="color: #000000;">{context}</span>'
    
    positions = sorted(match_positions, key=lambda x: x[0])
    html_parts = []
    last_end = 0
    
    for start, end in positions:
        if start > last_end:
            html_parts.append(f'<span style="color: #000000;">{context[last_end:start]}</span>')
        html_parts.append(
            f'<span style="background-color: #FFFF00; font-weight: bold; '
            f'padding: 2px 4px; border-radius: 2px; color: #000000;">{context[start:end]}</span>'
        )
        last_end = end
    
    if last_end < len(context):
        html_parts.append(f'<span style="color: #000000;">{context[last_end:]}</span>')
    
    return ''.join(html_parts)


def perform_hybrid_search(directory, keyword, whole_word, file_types, progress_callback):
    """Perform search using hybrid engine"""
    
    files = get_all_files(directory, file_types)
    
    if not files:
        return None, None
    
    # Initialize hybrid search engine
    settings = st.session_state.user_settings
    engine = HybridSearchEngine(
        search_mode=settings.performance.search_mode,
        index_enabled=settings.index.enabled
    )
    
    # Store for stop button
    st.session_state.search_engine = engine
    
    # Search
    results = engine.search_files(
        files=files,
        keyword=keyword,
        case_sensitive=False,
        whole_word=whole_word,
        progress_callback=progress_callback
    )
    
    completed = len([r for r in results.values() if r])
    total = len(files)
    
    return results, (completed, total)


def render_index_settings_section(settings):
    """Render index and search mode settings"""
    st.markdown("---")
    st.subheader("🗂️ Index & Search Mode Settings")
    
    # Search Mode Selection
    search_mode_options = {
        'hybrid': '🔥 Hybrid (Recommended) - Index + Fast Extract',
        'fast_extract': '⚡ Phase 1: Fast Extract Only (No Index)',
        'indexed_only': '📚 Phase 2: Indexed Search Only (Pre-indexed files)'
    }
    
    current_mode = settings.performance.search_mode
    
    selected_mode = st.selectbox(
        "Search Mode:",
        options=list(search_mode_options.keys()),
        format_func=lambda x: search_mode_options[x],
        index=list(search_mode_options.keys()).index(current_mode),
        key='search_mode_selector',
        help=(
            "**Hybrid**: Uses index for known files, extracts new ones (FASTEST)\n\n"
            "**Fast Extract**: Always extracts, no indexing (One-time searches)\n\n"
            "**Indexed Only**: Only pre-indexed files (INSTANT)"
        )
    )
    
    if selected_mode != current_mode:
        settings.performance.search_mode = selected_mode
        settings.profile = 'custom'
        st.session_state.settings_changed = True
    
    # Mode descriptions
    if selected_mode == 'hybrid':
        st.info("🔥 **Hybrid Mode (Default)**\n"
                "- First search: Builds index (15-30s for 200 files)\n"
                "- Second search: Uses index (< 1s)\n"
                "- New files: Auto-indexed\n"
                "- **Best for: Regular use**")
    elif selected_mode == 'fast_extract':
        st.info("⚡ **Phase 1: Fast Extract**\n"
                "- Uses PyMuPDF + Multithreading\n"
                "- No indexing, no persistence\n"
                "- Each search: 10-20s for 200 files\n"
                "- **Best for: One-time searches**")
    else:
        st.info("📚 **Phase 2: Indexed Only**\n"
                "- Only searches pre-indexed files\n"
                "- Instant results (< 1s)\n"
                "- Requires pre-indexing\n"
                "- **Best for: Static document sets**")
    
    # Index Settings
    col1, col2 = st.columns(2)
    
    with col1:
        index_enabled = st.checkbox(
            "Enable Document Index",
            value=settings.index.enabled,
            help="Persistent index for instant repeat searches",
            key='index_enabled_checkbox'
        )
        
        if index_enabled != settings.index.enabled:
            settings.index.enabled = index_enabled
            settings.profile = 'custom'
            st.session_state.settings_changed = True
    
    with col2:
        auto_index = st.checkbox(
            "Auto-Index New Files",
            value=settings.index.auto_index,
            disabled=not index_enabled,
            help="Automatically index files during search",
            key='auto_index_checkbox'
        )
        
        if auto_index != settings.index.auto_index:
            settings.index.auto_index = auto_index
            settings.profile = 'custom'
            st.session_state.settings_changed = True
    
    # Index Statistics
    if index_enabled:
        st.markdown("**Index Statistics:**")
        
        try:
            index = DocumentIndex(settings.index.index_path)
            stats = index.get_stats()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Indexed Files", stats['indexed_files'])
            col2.metric("Index Size", f"{stats['db_size_mb']:.1f} MB")
            col3.metric("Content Size", f"{stats['total_size_mb']:.1f} MB")
            
            # Index management
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Clear Index", key='clear_index_button'):
                    index.clear_index()
                    st.success("Index cleared!")
            
            with col2:
                if st.button("🔄 Rebuild Index", key='rebuild_index_button'):
                    index.clear_index()
                    st.success("Index will be rebuilt on next search")
                    
        except Exception as e:
            st.error(f"Could not load index stats: {e}")


def render_settings_tab():
    """Render the settings tab with all configuration options"""
    st.header("⚙️ Advanced Settings")
    
    settings = st.session_state.user_settings

    # Performance Profile Selection
    
    st.subheader("📊 Performance Profile")
    
    profile_options = {
        'low_resource': '🔋 Low Resource (2 workers, minimal memory)',
        'balanced': '⚖️ Balanced (8 workers, recommended)',
        'high_performance': '⚡ High Performance (16 workers, fast)',
        'maximum': '🚀 Maximum (32 workers, requires powerful system)',
        'custom': '🎛️ Custom (configure manually)'
    }
    
    current_profile = settings.profile if settings.profile in profile_options else 'custom'
    
    selected_profile = st.selectbox(
        "Choose a profile:",
        options=list(profile_options.keys()),
        format_func=lambda x: profile_options[x],
        index=list(profile_options.keys()).index(current_profile),
        key='profile_selector'
    )
    
    if selected_profile != 'custom' and selected_profile != current_profile and not st.session_state.prevent_rerun:
        st.session_state.user_settings = SettingsManager.get_preset(selected_profile)
        st.session_state.settings_changed = True
        st.session_state.prevent_rerun = True
        st.rerun()
    
    if st.session_state.prevent_rerun:
        st.session_state.prevent_rerun = False
    
    st.markdown("---")
    
    # System Information
    with st.expander("💻 System Information", expanded=False):
        try:
            cpu_count = os.cpu_count() or 1
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("CPU Cores", cpu_count)
                st.metric("CPU Usage", f"{cpu_percent}%")
            with col2:
                st.metric("Total RAM", f"{memory.total / (1024**3):.1f} GB")
                st.metric("Available RAM", f"{memory.available / (1024**3):.1f} GB")
            
            if cpu_count >= 8 and memory.available / (1024**3) > 4:
                st.success("✅ Recommended: High Performance or Maximum")
            elif cpu_count >= 4:
                st.info("ℹ️ Recommended: Balanced")
            else:
                st.warning("⚠️ Recommended: Low Resource")
        except Exception as e:
            st.error(f"Could not retrieve system info: {e}")
    
    st.markdown("---")
    
    # Performance Settings
    st.subheader("🖥️ Performance Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_workers = st.slider(
            "Max Workers (parallel threads)",
            min_value=1,
            max_value=32,
            value=settings.performance.max_workers,
            help="More workers = faster search, but uses more CPU",
            key='max_workers_slider'
        )
        
        min_batching = st.slider(
            "Min Files for Batching",
            min_value=10,
            max_value=200,
            value=settings.performance.min_files_for_batching,
            help="Files threshold to enable batching",
            key='min_batching_slider'
        )
    
    with col2:
        batch_size = st.slider(
            "Batch Size",
            min_value=10,
            max_value=500,
            value=settings.performance.batch_size,
            help="Number of files per batch",
            key='batch_size_slider'
        )
    
    if (max_workers != settings.performance.max_workers or
        batch_size != settings.performance.batch_size or
        min_batching != settings.performance.min_files_for_batching):
        settings.performance.max_workers = max_workers
        settings.performance.batch_size = batch_size
        settings.performance.min_files_for_batching = min_batching
        settings.profile = 'custom'
        st.session_state.settings_changed = True
    
    st.markdown("---")
    
    # Context Settings
    st.subheader("📝 Context Display Settings")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sentences_before = st.slider(
            "Sentences Before Match",
            min_value=1,
            max_value=5,
            value=settings.context.sentences_before,
            key='sentences_before_slider'
        )
    
    with col2:
        sentences_after = st.slider(
            "Sentences After Match",
            min_value=0,
            max_value=10,
            value=settings.context.sentences_after,
            key='sentences_after_slider'
        )
    
    with col3:
        merge_distance = st.slider(
            "Max Merge Distance",
            min_value=3,
            max_value=10,
            value=settings.context.max_merge_distance,
            help="Maximum sentences between matches to merge them",
            key='merge_distance_slider'
        )
    
    if (sentences_before != settings.context.sentences_before or
        sentences_after != settings.context.sentences_after or
        merge_distance != settings.context.max_merge_distance):
        settings.context.sentences_before = sentences_before
        settings.context.sentences_after = sentences_after
        settings.context.max_merge_distance = merge_distance
        settings.profile = 'custom'
        st.session_state.settings_changed = True
    
    st.markdown("---")
    
    # Cache Settings
    st.subheader("💾 Cache & Memory Settings")
    
    cache_enabled = st.checkbox(
        "Enable Text Caching",
        value=settings.cache.enabled,
        help="Cache extracted text for faster repeated searches",
        key='cache_enabled_checkbox'
    )
    
    if cache_enabled:
        col1, col2 = st.columns(2)
        
        with col1:
            cache_size = st.slider(
                "Cache Size Limit (MB)",
                min_value=100,
                max_value=2000,
                value=settings.cache.max_size_mb,
                step=100,
                key='cache_size_slider'
            )
            
            persistent_cache = st.checkbox(
                "Persistent Cache (save to disk)",
                value=settings.cache.persistent,
                help="Keep cache between app restarts (slower but persistent)",
                key='persistent_cache_checkbox'
            )
        
        with col2:
            auto_threshold = st.slider(
                "Auto Pre-extract Threshold",
                min_value=50,
                max_value=500,
                value=settings.cache.auto_preextract_threshold,
                help="Auto-suggest pre-extraction when file count exceeds this",
                key='auto_threshold_slider'
            )
            
            if st.session_state.text_cache:
                try:
                    stats = st.session_state.text_cache.get_stats()
                    st.metric("Cache Usage", f"{stats['size_mb']:.1f} / {stats['max_size_mb']} MB")
                    st.metric("Cached Files", stats['entries'])
                    
                    if st.button("🗑️ Clear Cache", key='clear_cache_button'):
                        st.session_state.text_cache.clear()
                        st.session_state.extracted_texts = {}
                        st.success("Cache cleared!")
                except Exception as e:
                    st.error(f"Error getting cache stats: {e}")
        
        if (cache_size != settings.cache.max_size_mb or
            persistent_cache != settings.cache.persistent or
            auto_threshold != settings.cache.auto_preextract_threshold):
            settings.cache.max_size_mb = cache_size
            settings.cache.persistent = persistent_cache
            settings.cache.auto_preextract_threshold = auto_threshold
            settings.profile = 'custom'
            st.session_state.settings_changed = True
            
            st.session_state.text_cache = TextCache(
                max_size_mb=cache_size,
                persistent=persistent_cache
            )
    
    if cache_enabled != settings.cache.enabled:
        settings.cache.enabled = cache_enabled
        settings.profile = 'custom'
        st.session_state.settings_changed = True
        
        if cache_enabled:
            st.session_state.text_cache = TextCache(
                max_size_mb=settings.cache.max_size_mb,
                persistent=settings.cache.persistent
            )
        else:
            st.session_state.text_cache = None
    
    # Index Settings Section
    render_index_settings_section(settings)
    
    st.markdown("---")
    
    # Action Buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Settings", use_container_width=True, key='save_settings_button'):
            SettingsManager.save_settings(settings)
            Config.apply_user_settings(settings)
            st.session_state.settings_changed = False
            st.success("✅ Settings saved!")
    
    with col2:
        if st.button("🔄 Reset to Balanced", use_container_width=True, key='reset_settings_button'):
            st.session_state.user_settings = SettingsManager.get_preset('balanced')
            SettingsManager.save_settings(st.session_state.user_settings)
            Config.apply_user_settings(st.session_state.user_settings)
            st.session_state.settings_changed = False
            if st.session_state.user_settings.cache.enabled:
                st.session_state.text_cache = TextCache(
                    max_size_mb=st.session_state.user_settings.cache.max_size_mb,
                    persistent=st.session_state.user_settings.cache.persistent
                )
            else:
                st.session_state.text_cache = None
            st.success("✅ Reset to balanced settings!")
    
    with col3:
        if st.button("↩️ Discard Changes", use_container_width=True, key='discard_changes_button'):
            st.session_state.user_settings = SettingsManager.load_settings()
            st.session_state.settings_changed = False
            st.info("ℹ️ Changes discarded")
    
    if st.session_state.settings_changed:
        st.warning("⚠️ You have unsaved changes. Click 'Save Settings' to apply them.")


def main():
    """Main application"""
    
    # Apply current settings to Config
    try:
        Config.apply_user_settings(st.session_state.user_settings)
    except Exception as e:
        st.error(f"Error applying settings: {e}")
        st.session_state.user_settings = SettingsManager.get_preset('balanced')
        Config.apply_user_settings(st.session_state.user_settings)
    
    # Header
    st.title(f"{Config.PAGE_ICON} Document Keyword Search Tool")
    st.markdown("Search for keywords across PDF, DOCX, and DOC files with **ultra-fast hybrid search**, **parallel processing**, and **persistent indexing**")
    
    # Create tabs
    #tab1, tab2 = st.tabs(["🔍 Search", "⚙️ Settings"])
    tab1, tab2, tab3 = st.tabs(["🔍 Search", "⚙️ Settings", "💬 Chat with Documents"])
    
    # ==================== TAB 1: SEARCH ====================
    with tab1:
        # Sidebar for search configuration
        with st.sidebar:
            st.header("🔍 Search Configuration")
            
            # Folder picker - FIXED: Prevent double opening
            st.subheader("📁 Select Document Folder")
            
            # Directory input
            directory_input = st.text_input(
                "Directory Path",
                value=st.session_state.selected_directory,
                help="Enter the path or use Browse button",
                key='directory_input_field'
            )
            
            # Browse button
            if st.button("📂 Browse Folder", use_container_width=True, key='browse_folder_btn'):
                # Set flag to prevent double execution
                st.session_state.folder_picker_clicked = True
                
                # Open folder picker using tkinter
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    
                    root = tk.Tk()
                    root.withdraw()
                    root.wm_attributes('-topmost', 1)
                    
                    folder_path = filedialog.askdirectory(
                        title='Select Document Folder',
                        initialdir=st.session_state.selected_directory
                    )
                    
                    root.destroy()
                    
                    if folder_path:
                        st.session_state.selected_directory = folder_path
                        st.rerun()
                except Exception as e:
                    st.error(f"Error opening folder picker: {e}")
            
            # Update from text input
            if directory_input != st.session_state.selected_directory and not st.session_state.folder_picker_clicked:
                st.session_state.selected_directory = directory_input
            
            # Reset flag
            st.session_state.folder_picker_clicked = False
            
            st.markdown("---")
            
            keyword = st.text_input(
                "🔍 Search Keyword/Phrase",
                help="Enter the keyword or phrase to search for"
            )
            
            st.subheader("Search Options")
            
            st.info("🔹 Search is **always case-insensitive** for better matching")
            st.info("🔹 Automatically matches word variations (e.g., 'low-resource' matches 'low resource' and 'low resources')")
            
            # Show current profile and mode
            current_settings = st.session_state.user_settings
            profile_name = current_settings.profile.replace('_', ' ').title()
            mode_name = {
                'hybrid': 'Hybrid 🔥',
                'fast_extract': 'Fast Extract ⚡',
                'indexed_only': 'Indexed Only 📚'
            }.get(current_settings.performance.search_mode, 'Hybrid')
            
            st.info(f"🎛️ **Profile:** {profile_name}\n\n"
                   f"**Mode:** {mode_name}\n\n"
                   f"Workers: {current_settings.performance.max_workers} | "
                   f"Index: {'✓' if current_settings.index.enabled else '✗'}")
            
            whole_word = st.checkbox("Whole Word Match", value=False)
            
            file_types = st.multiselect(
                "File Types",
                options=['.pdf', '.docx', '.doc'],
                default=['.pdf', '.docx', '.doc']
            )
            
            auto_highlight = st.checkbox(
                "Auto-generate highlighted documents",
                value=False,  # CHANGED TO FALSE to prevent hanging
                help="Generate highlighted versions (may take extra time for many files)"
            )
            
            st.markdown("---")
            
            # Search and Stop buttons
            col1, col2 = st.columns(2)
            
            with col1:
                search_button = st.button(
                    "🔍 Search", 
                    type="primary", 
                    use_container_width=True,
                    disabled=st.session_state.searching
                )
            
            with col2:
                stop_button = st.button(
                    "⏹️ Stop", 
                    type="secondary", 
                    use_container_width=True,
                    disabled=not st.session_state.searching
                )
        
        # Handle stop button
        if stop_button and st.session_state.searching:

            # Set stop flag in search engine
            st.session_state.searching = False
            st.session_state.search_stopped = True

            # Stop the search engine
            if hasattr(st.session_state, 'search_engine') and st.session_state.search_engine:
                st.session_state.search_engine.stop()

            
            # Force a rerun to update UI
            #st.session_state.searching = False
            #st.session_state.search_stopped = True
            st.warning("⏹️ Search stopped by user")
            st.rerun()
        
        # Main content area - Search
        if search_button:
            if not keyword:
                st.error("Please enter a search keyword")
            elif not os.path.exists(st.session_state.selected_directory):
                st.error(f"Directory not found: {st.session_state.selected_directory}")
            else:
                st.session_state.search_results = None
                st.session_state.processed_results = None
                st.session_state.highlighted_files = {}
                st.session_state.search_stopped = False

                # Clear extraction cache from previous search
                if hasattr(st.session_state, 'search_engine') and st.session_state.search_engine:
                    if hasattr(st.session_state.search_engine.extractor, 'clear_cache'):
                        st.session_state.search_engine.extractor.clear_cache()
                
                st.session_state.searching = True
                st.session_state.search_stopped = False
                
                # Create placeholders
                progress_container = st.empty()
                status_container = st.empty()
                
                try:
                    def update_progress(current, total, filename):
                        progress = current / total
                        progress_container.progress(progress, text=f"Searching: {filename} ({current}/{total})")
                    
                    # Hybrid search
                    results, completion_stats = perform_hybrid_search(
                        st.session_state.selected_directory, keyword, whole_word, file_types, update_progress
                    )
                    
                    # Clear progress indicators
                    progress_container.empty()
                    status_container.empty()

                    # Check if search was stopped
                    if st.session_state.get('search_stopped', False):
                        st.session_state.searching = False
                        st.warning("⏹️ Search stopped. Showing partial results.")

                    else:
                        st.session_state.searching = False
                    
                    if results is None:
                        st.session_state.searching = False
                    else:
                        st.session_state.completion_stats = completion_stats
                        
                        # Process results
                        if results:
                            processor = ResultProcessor()
                            processed_results = processor.process_results(results)
                            st.session_state.processed_results = processed_results
                        else:
                            st.session_state.processed_results = {}
                        
                        st.session_state.search_results = results
                        
                        # Success message
                        completed, total = completion_stats
                        if st.session_state.search_stopped:
                            st.warning(f"⏹️ Search stopped. Results from {completed} files.")
                        else:
                            settings = st.session_state.user_settings
                            mode_display = {
                                'hybrid': 'Hybrid 🔥',
                                'fast_extract': 'Fast Extract ⚡',
                                'indexed_only': 'Indexed Only 📚'
                            }.get(settings.performance.search_mode, 'Hybrid')
                            
                            st.success(f"✅ Search completed using **{mode_display}** mode! "
                                      f"Found matches in {len(results)} files.")
                            
                            # Show index stats
                            if settings.index.enabled and hasattr(st.session_state, 'search_engine'):
                                try:
                                    idx_stats = st.session_state.search_engine.get_index_stats()
                                    st.info(f"📊 Index: {idx_stats['indexed_files']} files indexed "
                                           f"({idx_stats['db_size_mb']:.1f} MB)")
                                except:
                                    pass
                        
                        # FIXED: Only highlight if explicitly enabled and results exist
                        if auto_highlight and results and not st.session_state.search_stopped and len(results) <= 20:
                            # Limit to 20 files to prevent hanging
                            with st.spinner("✨ Generating highlighted documents (this may take a moment)..."):
                                try:
                                    manager = SearchManager()
                                    highlighter = DocumentHighlighter(manager)
                                    highlighted = highlighter.highlight_all_results(results, keyword, False)
                                    st.session_state.highlighted_files = highlighted
                                    st.info(f"✅ Highlighted {len(highlighted)} documents")
                                except Exception as e:
                                    st.warning(f"Could not generate highlighted documents: {e}")
                        elif auto_highlight and len(results) > 20:
                            st.warning("⚠️ Too many files for auto-highlighting. Download individual files manually.")
                
                
                except Exception as e:
                    st.error(f"Error during search: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                
                finally:
                    # CRITICAL: Always set searching to False
                    st.session_state.searching = False
        
        # Display results
        if st.session_state.processed_results is not None:
            processed_results = st.session_state.processed_results
            raw_results = st.session_state.search_results
            
            if not processed_results:
                st.info("🔍 No matches found for the given keyword")
            else:
                # Summary metrics
                total_matches = sum(len(raw_results.get(fp, [])) for fp in processed_results.keys())
                total_files = len(processed_results)
                completed, total_searched = st.session_state.completion_stats
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📄 Files with Matches", total_files)
                col2.metric("🎯 Total Matches", total_matches)
                col3.metric("🔍 Search Term", f'"{keyword}"')
                col4.metric("⚡ Files Searched", f"{completed}/{total_searched}" if st.session_state.search_stopped else completed)
                
                st.markdown("---")
                
                # Results by file
                for file_path, merged_matches in processed_results.items():
                    total_matches_in_file = sum(m.match_count for m in merged_matches)
                    
                    with st.expander(
                        f"📄 {Path(file_path).name} ({total_matches_in_file} matches on {len(merged_matches)} page{'s' if len(merged_matches) != 1 else ''})", 
                        expanded=False
                    ):
                        st.caption(f"**Path:** {file_path}")
                        st.caption(f"**Size:** {get_file_size(file_path)}")
                        
                        st.markdown("### Matches")
                        
                        for idx, merged in enumerate(merged_matches, 1):
                            st.markdown(f"**Page {merged.page_number}** ({merged.match_count} match{'es' if merged.match_count > 1 else ''})")
                            
                            context = merged.merged_context
                            highlighted_html = build_highlighted_html(context, merged.match_positions)
                            
                            st.markdown(
                                f'<div style="background-color: #f8f9fa; padding: 12px; border-radius: 5px; '
                                f'margin: 8px 0; border-left: 3px solid #007bff; color: #000000; '
                                f'font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif;">'
                                f'{highlighted_html}'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                            
                            if idx < len(merged_matches):
                                st.markdown("<div style='margin: 10px 0;'></div>", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Download highlighted file - FIXED: Don't auto-load, generate on demand
                        if st.button(f"🎨 Generate Highlighted PDF", key=f"gen_highlight_{file_path}", use_container_width=True):
                            with st.spinner(f"Generating highlighted version of {Path(file_path).name}..."):
                                try:
                                    manager = SearchManager()
                                    highlighter = DocumentHighlighter(manager)
                                    
                                    # Generate single file highlight
                                    output_path = highlighter._generate_output_path(file_path, keyword)
                                    ext = Path(file_path).suffix.lower()
                                    searcher = manager.get_searcher(ext)
                                    
                                    if searcher:
                                        success = searcher.highlight_document(file_path, keyword, output_path, False)
                                        
                                        if success and os.path.exists(output_path):
                                            with open(output_path, 'rb') as f:
                                                st.download_button(
                                                    label="📥 Download Highlighted Document",
                                                    data=f,
                                                    file_name=Path(output_path).name,
                                                    mime="application/octet-stream",
                                                    key=f"download_gen_{file_path}",
                                                    use_container_width=True
                                                )
                                            st.success("✅ Highlighted document ready!")
                                        else:
                                            st.error("Failed to generate highlighted document")
                                    else:
                                        st.error(f"No highlighter available for {ext} files")
                                except Exception as e:
                                    st.error(f"Error highlighting: {e}")



            
                
                # Export results to Excel
                st.markdown("---")
                st.subheader("📊 Export Results")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📥 Export to Excel", use_container_width=True, key='export_excel_btn'):
                        try:
                            df_data = []
                            for file_path, matches in raw_results.items():
                                for match in matches:
                                    df_data.append({
                                        'File Name': match.file_name,
                                        'File Path': file_path,
                                        'Page Number': match.page_number,
                                        'Matched Text': match.matched_text,
                                        'Context': match.context
                                    })
                            
                            df = pd.DataFrame(df_data)
                            excel_file = Config.OUTPUT_DIR / f"search_results_{keyword[:20].replace(' ', '_')}.xlsx"
                            df.to_excel(excel_file, index=False, engine='openpyxl')
                            
                            st.success(f"✅ Results exported to: {excel_file.name}")
                            
                            with open(excel_file, 'rb') as f:
                                st.download_button(
                                    label="📥 Download Excel Report",
                                    data=f,
                                    file_name=excel_file.name,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key='download_excel_report',
                                    use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Error exporting: {e}")
                
                with col2:
                    if st.button("📋 Export to DOCX", use_container_width=True, key='export_docx_btn'):
                        try:
                            from datetime import datetime
                            docx_file = Config.OUTPUT_DIR / f"combined_results_{keyword[:20].replace(' ', '_')}.docx"

                            export_combined_results_to_docx(
                                raw_results, keyword, str(docx_file))
                            st.success(f"✅ Combined DOCX created")
                            with open(docx_file, 'rb') as f:
                                st.download_button(
                                    label="📥 Download Combined DOCX",
                                    data=f,
                                    file_name=docx_file.name,
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    key='download_docx_report',
                                    use_container_width=True
                                )

                        except Exception as e:
                            st.error(f"Error exporting to DOCX: {e}")
                            import traceback
                            st.code(traceback.format_exc())

                with col3:

                    if st.button("📕 Export to PDF", use_container_width=True, key='export_pdf_btn'):

                        try:
                            from datetime import datetime
                            pdf_file = Config.OUTPUT_DIR / f"combined_results_{keyword[:20].replace(' ', '_')}.pdf"
            
                            export_combined_results_to_pdf(raw_results, keyword, str(pdf_file))
            
                            st.success(f"✅ Combined PDF created!")
            
                            with open(pdf_file, 'rb') as f:
                                st.download_button(
                                    label="📥 Download PDF",
                                    data=f,
                                    file_name=pdf_file.name,
                                    mime="application/pdf",
                                    key='download_pdf_report',
                                    use_container_width=True
                                )

                        except Exception as e:
                            st.error(f"Error exporting to PDF: {e}")
                            import traceback
                            st.code(traceback.format_exc())

                st.info("💡 **Tip:** The DOCX and PDF exports combine all results into a single document with file headers and page citations.")
                                        
                                    #st.info("💡 **Tip:** Use 'Generate Highlighted PDF' buttons in each file section to create highlighted versions on demand.")
    
    # ==================== TAB 2: SETTINGS ====================
    with tab2:
        render_settings_tab()


    # ==================== TAB 3: CHAT WITH DOCUMENTS ====================
    # ==================== TAB 3: CHAT WITH DOCUMENTS ====================
 # ==================== TAB 3: CHAT WITH DOCUMENTS ====================
    with tab3:
        st.header("💬 Chat with Your Documents")
        st.markdown("Ask questions and get AI-powered answers from your documents")
        
        # Check if documents exist first
        document_dir = st.session_state.get('selected_directory', './documents')
        has_documents = False
        files = []
        
        if os.path.exists(document_dir):
            files = get_all_files(document_dir, Config.SUPPORTED_EXTENSIONS)
            has_documents = len(files) > 0
        
        # Initialize flag check
        if not st.session_state.get('rag_initialized', False):
            # Show initialization page
            st.info("🚀 **RAG system not initialized yet.**")
            
            # Check for documents FIRST
            if not has_documents:
                st.warning("⚠️ **No documents found!**")
                st.markdown(f"""
                Please ensure you have documents in the directory: `{document_dir}`
                
                You can:
                1. Go to the **Search tab** to select a different directory
                2. Add PDF, DOCX, or DOC files to `{document_dir}`
                3. Come back here to initialize RAG
                """)
                return  # Stop here if no documents
            
            st.success(f"✅ Found {len(files)} documents ready to index!")
            
            st.markdown("### 📋 Prerequisites Check:")
            st.markdown("Before initializing, ensure you have:")
            
            # Check 1: Documents (already done)
            st.markdown(f"1. ✅ **Ollama installed** → [Download](https://ollama.com/download)")
            st.markdown(f"2. ✅ **A model pulled** → Run in terminal: `ollama pull llama3.2`")
            st.markdown(f"3. ✅ **Documents ready** → {len(files)} files found")
            
            st.info("**Note:** First-time setup downloads embedding model (~90MB, one-time). This takes 1-2 minutes. Subsequent uses are instant.")
            
            # Check if Ollama is available - FIXED VERSION
            ollama_available = False
            ollama_models = []
            ollama_error = None
            
            try:
                import ollama
                
                # Try to list models with better error handling
                try:
                    models_response = ollama.list()
                    
                    # Handle different response formats
                    if isinstance(models_response, dict):
                        model_list = models_response.get('models', [])
                    else:
                        model_list = models_response if isinstance(models_response, list) else []
                    
                    # Extract model names safely
                    for m in model_list:
                        if isinstance(m, dict):
                            name = m.get('name') or m.get('model') or m.get('id')
                            if name:
                                ollama_models.append(name)
                        elif isinstance(m, str):
                            ollama_models.append(m)
                    
                    if ollama_models:
                        st.success(f"✅ Ollama detected! Available models: {', '.join(ollama_models)}")
                        ollama_available = True
                    else:
                        st.warning("⚠️ Ollama is running but no models found.")
                        st.code("# Pull a model:\nollama pull llama3.2")
                        ollama_error = "No models installed"
                        
                except Exception as list_error:
                    st.error(f"❌ Ollama not responding: {str(list_error)}")
                    st.markdown("""
                    **Troubleshooting:**
                    1. Make sure Ollama is installed
                    2. Check if Ollama service is running
                    3. Try running: `ollama list` in your terminal
                    """)
                    ollama_error = str(list_error)
                    
            except ImportError:
                st.error("❌ Ollama Python package not installed.")
                st.code("pip install ollama")
                ollama_error = "Package not installed"
            except Exception as e:
                st.error(f"❌ Unexpected error checking Ollama: {str(e)}")
                ollama_error = str(e)
            
            # Show installation instructions if not available
            if not ollama_available:
                with st.expander("📦 Install Ollama"):
                    st.code("""# Windows:
winget install Ollama.Ollama

# Mac:
brew install ollama

# Linux:
curl -fsSL https://ollama.com/install.sh | sh

# After installation, pull a model:
ollama pull llama3.2

# Verify:
ollama list""")
            
            # Initialize button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                # Enable button if we have documents (allow initialization even if Ollama check fails - it might work anyway)
                can_initialize = has_documents
                
                if not can_initialize:
                    st.warning("⚠️ Need documents to initialize")
                elif not ollama_available:
                    st.warning("⚠️ Ollama may not be available, but you can try initializing anyway")
                
                init_button = st.button(
                    "⚡ Initialize RAG System", 
                    type="primary", 
                    use_container_width=True, 
                    key='init_rag_btn',
                    disabled=not can_initialize,  # Only require documents, not Ollama check
                    help="Initialize the RAG system with your documents"
                )
                
                if init_button and can_initialize:
                    # Use simple spinner instead of complex progress display
                    with st.spinner("🚀 Initializing RAG system... This may take 1-2 minutes."):
                        try:
                            # Lazy import - only import when button is clicked
                            from core.rag_engine import RAGEngine
                            
                            # Initialize RAG engine
                            rag_engine = RAGEngine(
                                model_name="llama3.2:latest",
                                embedding_model="all-MiniLM-L6-v2",
                                vector_db_path="vector_store"
                            )
                            
                            # Check if it actually worked
                            if not rag_engine.llm.is_available():
                                st.error("❌ RAG initialized but Ollama is not available!")
                                st.markdown("""
                                **Please:**
                                1. Install Ollama: https://ollama.com/download
                                2. Pull a model: `ollama pull llama3.2`
                                3. Try initializing again
                                """)
                                st.session_state.rag_initialized = False
                                st.session_state.rag_engine = None
                            else:
                                # Success!
                                st.session_state.rag_engine = rag_engine
                                st.session_state.rag_initialized = True
                                st.success("✅ RAG system initialized successfully!")
                                st.balloons()
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"❌ Error initializing RAG: {e}")
                            
                            # Detailed error info
                            with st.expander("🐛 Error Details"):
                                import traceback
                                st.code(traceback.format_exc())
                            
                            # Specific error help
                            error_str = str(e).lower()
                            if 'ollama' in error_str or 'connection' in error_str:
                                st.markdown("""
                                **This looks like an Ollama connection issue:**
                                1. Install Ollama: https://ollama.com/download
                                2. Make sure it's running: `ollama list`
                                3. Pull a model: `ollama pull llama3.2`
                                """)
                            elif 'torch' in error_str or 'dll' in error_str:
                                st.markdown("""
                                **This looks like a PyTorch issue:**
                                ```bash
                                pip uninstall torch torchvision torchaudio -y
                                pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
                                ```
                                """)
                            
                            st.session_state.rag_initialized = False
                            st.session_state.rag_engine = None
            
            # Show helpful info
            with st.expander("ℹ️ What is RAG?"):
                st.markdown("""
                **RAG (Retrieval-Augmented Generation)** allows you to:
                - 🤖 Ask questions in natural language
                - 📚 Get answers from YOUR documents only
                - 📖 See citations and sources automatically
                - 💬 Have context-aware conversations
                - 🔍 Reason across multiple documents
                
                Everything runs **locally** - 100% free, no API costs!
                """)
            
            return  # Stop here if not initialized
        
        # RAG is initialized - get the engine safely
        rag_engine = st.session_state.get('rag_engine')
        
        if rag_engine is None:
            st.error("❌ RAG engine initialization failed. Please try again.")
            if st.button("🔄 Retry Initialization", key='retry_rag_btn'):
                st.session_state.rag_initialized = False
                st.rerun()
            return
        
        # Double-check LLM is available
        if not rag_engine.llm.is_available():
            st.error("❌ RAG initialized but Ollama is not responding!")
            st.markdown("""
            **Please check:**
            1. Is Ollama installed? Run: `ollama --version`
            2. Are models available? Run: `ollama list`
            3. Try: `ollama pull llama3.2`
            
            After fixing, click below to retry:
            """)
            if st.button("🔄 Retry Connection", key='retry_ollama_btn'):
                st.session_state.rag_initialized = False
                st.rerun()
            return
    
       
        
        # Sidebar for RAG configuration
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
                
                selected_model = st.selectbox(
                    "LLM Model:",
                    options=available_models,
                    index=available_models.index(current_model) if current_model in available_models else 0,
                    help="Select the Ollama model to use",
                    key='rag_model_select'
                )
                
                if selected_model != current_model:
                    if st.button("🔄 Switch Model", use_container_width=True, key='switch_model_btn'):
                        with st.spinner(f"Switching to {selected_model}..."):
                            success = rag_engine.switch_model(selected_model)
                            if success:
                                st.success(f"✅ Switched to {selected_model}")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to switch to {selected_model}")
            else:
                st.warning("No Ollama models found")
                st.code("ollama pull llama3.2")
            
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
                if st.button("💾 Export", use_container_width=True, key='export_chat_btn'):
                    if conv_stats['total_messages'] > 0:
                        filepath = rag_engine.export_conversation()
                        if filepath:
                            st.success(f"✅ Exported!")
                            
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
            st.markdown("""
            ### 🚀 Quick Start:
            
            1. Click **"🔄 Index Documents"** in the sidebar
            2. Select your document directory
            3. Click **"▶️ Start Indexing"**
            4. Wait for indexing to complete
            5. Start asking questions!
            """)
            return
        
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
        if prompt := st.chat_input("Ask a question about your documents...", key='chat_input'):
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
                
                # Streaming response
                full_response = ""
                
                try:
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
                    
                except Exception as e:
                    error_msg = f"❌ Error generating response: {e}"
                    message_placeholder.error(error_msg)
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': error_msg,
                        'citations': []
                    })
        
        # Tips section at bottom (only show if no messages)
        if len(st.session_state.chat_messages) == 0:
            st.markdown("---")
            st.markdown("### 💡 Tips:")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **Ask Specific Questions:**
                - "What is named entity recognition?"
                - "Compare the approaches in document A and B"
                - "What are the main findings?"
                """)
            
            with col2:
                st.markdown("""
                **Features:**
                - ✅ Context-aware conversations
                - ✅ Multi-document reasoning
                - ✅ Automatic citations
                - ✅ 100% free & local
                """)

if __name__ == "__main__":
    main()