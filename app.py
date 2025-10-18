"""Streamlit application with Hybrid Search System - ALL BUGS FIXED"""

import streamlit as st
import pandas as pd
from pathlib import Path
import os
from typing import List, Tuple
import psutil

from core.hybrid_search_engine import HybridSearchEngine
from core.document_index import DocumentIndex
from core.result_processor import ResultProcessor
from core.highlighter import DocumentHighlighter
from core.search_manager import SearchManager
from core.settings_manager import SettingsManager, UserSettings
from core.cache_manager import TextCache
from core.text_extractor import TextExtractor
from config import Config
from utils.helpers import get_file_size, get_all_files

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
            min_value=1,
            max_value=5,
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
    tab1, tab2 = st.tabs(["🔍 Search", "⚙️ Settings"])
    
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
            if hasattr(st.session_state, 'search_engine') and st.session_state.search_engine:
                st.session_state.search_engine.stop()
            
            st.session_state.searching = False
            st.session_state.search_stopped = True
            st.warning("⏹️ Search stopped by user")
        
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
                
                col1, col2 = st.columns([1, 3])
                
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
                    st.info("💡 **Tip:** Use 'Generate Highlighted PDF' buttons in each file section to create highlighted versions on demand.")
    
    # ==================== TAB 2: SETTINGS ====================
    with tab2:
        render_settings_tab()


if __name__ == "__main__":
    main()