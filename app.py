"""Streamlit application with Settings Tab and Caching"""

import streamlit as st
import pandas as pd
from pathlib import Path
import os
from typing import List, Tuple
import psutil

from core.search_manager import SearchManager
from core.result_processor import ResultProcessor
from core.highlighter import DocumentHighlighter
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


def render_settings_tab():
    """Render the settings tab with all configuration options"""
    st.header("⚙️ Advanced Settings")
    
    settings = st.session_state.user_settings
    
    # Performance Profile Selection
    st.subheader("📊 Performance Profile")
    
    profile_options = {
        'low_resource': '🔋 Low Resource (2 workers, minimal memory)',
        'balanced': '⚖️ Balanced (16 workers, recommended)',
        'high_performance': '⚡ High Performance (32 workers, fast)',
        'maximum': '🚀 Maximum (64 workers, requires powerful system)',
        'custom': '🎛️ Custom (configure manually)'
    }
    
    current_profile = settings.profile if settings.profile in profile_options else 'custom'
    
    selected_profile = st.selectbox(
        "Choose a profile:",
        options=list(profile_options.keys()),
        format_func=lambda x: profile_options[x],
        index=list(profile_options.keys()).index(current_profile)
    )
    
    # Apply preset if changed
    if selected_profile != 'custom' and selected_profile != current_profile:
        settings = SettingsManager.get_preset(selected_profile)
        st.session_state.user_settings = settings
        st.session_state.settings_changed = True
        st.rerun()
    
    st.markdown("---")
    
    # System Information
    with st.expander("💻 System Information", expanded=False):
        cpu_count = os.cpu_count() or 1
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("CPU Cores", cpu_count)
            st.metric("CPU Usage", f"{cpu_percent}%")
        with col2:
            st.metric("Total RAM", f"{memory.total / (1024**3):.1f} GB")
            st.metric("Available RAM", f"{memory.available / (1024**3):.1f} GB")
        
        # Recommendation
        if cpu_count >= 8 and memory.available / (1024**3) > 4:
            st.success("✅ Recommended: High Performance or Maximum")
        elif cpu_count >= 4:
            st.info("ℹ️ Recommended: Balanced")
        else:
            st.warning("⚠️ Recommended: Low Resource")
    
    st.markdown("---")
    
    # Performance Settings
    st.subheader("🖥️ Performance Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_workers = st.slider(
            "Max Workers (parallel threads)",
            min_value=1,
            max_value=64,
            value=settings.performance.max_workers,
            help="More workers = faster search, but uses more CPU"
        )
        
        min_batching = st.slider(
            "Min Files for Batching",
            min_value=10,
            max_value=200,
            value=settings.performance.min_files_for_batching,
            help="Files threshold to enable batching"
        )
    
    with col2:
        batch_size = st.slider(
            "Batch Size",
            min_value=10,
            max_value=500,
            value=settings.performance.batch_size,
            help="Number of files per batch"
        )
    
    # Update settings if changed
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
            value=settings.context.sentences_before
        )
    
    with col2:
        sentences_after = st.slider(
            "Sentences After Match",
            min_value=1,
            max_value=5,
            value=settings.context.sentences_after
        )
    
    with col3:
        merge_distance = st.slider(
            "Max Merge Distance",
            min_value=3,
            max_value=10,
            value=settings.context.max_merge_distance,
            help="Maximum sentences between matches to merge them"
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
        help="Cache extracted text for faster repeated searches"
    )
    
    if cache_enabled:
        col1, col2 = st.columns(2)
        
        with col1:
            cache_size = st.slider(
                "Cache Size Limit (MB)",
                min_value=100,
                max_value=2000,
                value=settings.cache.max_size_mb,
                step=100
            )
            
            persistent_cache = st.checkbox(
                "Persistent Cache (save to disk)",
                value=settings.cache.persistent,
                help="Keep cache between app restarts (slower but persistent)"
            )
        
        with col2:
            auto_threshold = st.slider(
                "Auto Pre-extract Threshold",
                min_value=50,
                max_value=500,
                value=settings.cache.auto_preextract_threshold,
                help="Auto-suggest pre-extraction when file count exceeds this"
            )
            
            # Cache statistics
            if st.session_state.text_cache:
                stats = st.session_state.text_cache.get_stats()
                st.metric("Cache Usage", f"{stats['size_mb']:.1f} / {stats['max_size_mb']} MB")
                st.metric("Cached Files", stats['entries'])
                
                if st.button("🗑️ Clear Cache"):
                    st.session_state.text_cache.clear()
                    st.session_state.extracted_texts = {}
                    st.success("Cache cleared!")
                    st.rerun()
        
        if (cache_size != settings.cache.max_size_mb or
            persistent_cache != settings.cache.persistent or
            auto_threshold != settings.cache.auto_preextract_threshold):
            settings.cache.max_size_mb = cache_size
            settings.cache.persistent = persistent_cache
            settings.cache.auto_preextract_threshold = auto_threshold
            settings.profile = 'custom'
            st.session_state.settings_changed = True
            
            # Recreate cache with new settings
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
    
    st.markdown("---")
    
    # Action Buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Settings", use_container_width=True):
            SettingsManager.save_settings(settings)
            Config.apply_user_settings(settings)
            st.session_state.settings_changed = False
            st.success("✅ Settings saved!")
    
    with col2:
        if st.button("🔄 Reset to Balanced", use_container_width=True):
            st.session_state.user_settings = SettingsManager.get_preset('balanced')
            SettingsManager.save_settings(st.session_state.user_settings)
            Config.apply_user_settings(st.session_state.user_settings)
            st.session_state.settings_changed = False
            st.success("✅ Reset to balanced settings!")
            st.rerun()
    
    with col3:
        if st.button("↩️ Discard Changes", use_container_width=True):
            st.session_state.user_settings = SettingsManager.load_settings()
            st.session_state.settings_changed = False
            st.info("ℹ️ Changes discarded")
            st.rerun()
    
    if st.session_state.settings_changed:
        st.warning("⚠️ You have unsaved changes. Click 'Save Settings' to apply them.")


def main():
    """Main application"""
    
    # Apply current settings to Config
    Config.apply_user_settings(st.session_state.user_settings)
    
    # Header
    st.title(f"{Config.PAGE_ICON} Document Keyword Search Tool")
    st.markdown("Search for keywords across PDF, DOCX, and DOC files with **parallel processing**, **caching**, and **customizable settings**")
    
    # Create tabs
    tab1, tab2 = st.tabs(["🔍 Search", "⚙️ Settings"])
    
    # ==================== TAB 1: SEARCH ====================
    with tab1:
        # Sidebar for search configuration
        with st.sidebar:
            st.header("🔍 Search Configuration")
            
            directory = st.text_input(
                "📁 Directory Path",
                value="./documents",
                help="Enter the path to the directory containing your documents"
            )
            
            keyword = st.text_input(
                "🔍 Search Keyword/Phrase",
                help="Enter the keyword or phrase to search for"
            )
            
            st.subheader("Search Options")
            
            st.info("🔹 Search is **always case-insensitive** for better matching")
            st.info("🔹 Automatically matches word variations (e.g., 'low-resource' matches 'low resource' and 'low resources')")
            
            # Show current profile
            current_settings = st.session_state.user_settings
            profile_name = current_settings.profile.replace('_', ' ').title()
            st.info(f"🎛️ Current Profile: **{profile_name}**\n\n"
                   f"Workers: {current_settings.performance.max_workers} | "
                   f"Cache: {'✓' if current_settings.cache.enabled else '✗'}")
            
            whole_word = st.checkbox("Whole Word Match", value=False)
            
            file_types = st.multiselect(
                "File Types",
                options=['.pdf', '.docx', '.doc'],
                default=['.pdf', '.docx', '.doc']
            )
            
            auto_highlight = st.checkbox(
                "Auto-generate highlighted documents",
                value=True,
                help="Automatically create highlighted versions of matching documents"
            )
            
            # Pre-extraction option
            if directory and os.path.exists(directory):
                files = get_all_files(directory, file_types)
                file_count = len(files)
                
                if file_count > 0:
                    st.markdown("---")
                    st.subheader("⚡ Performance Options")
                    
                    # Smart auto-suggest for pre-extraction
                    if file_count >= current_settings.cache.auto_preextract_threshold:
                        st.warning(f"📊 {file_count} files detected. Pre-extraction recommended for multiple searches!")
                        use_preextract = st.checkbox(
                            "🚀 Pre-extract all text (faster for repeated searches)",
                            value=True,
                            help=f"Extract text from all {file_count} files upfront. First search slower, subsequent searches much faster!"
                        )
                    else:
                        use_preextract = st.checkbox(
                            "🚀 Pre-extract all text",
                            value=False,
                            help="Extract text from all files upfront for faster repeated searches"
                        )
                else:
                    use_preextract = False
            else:
                use_preextract = False
            
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
            if st.session_state.search_manager:
                st.session_state.search_manager.stop_search()
                st.session_state.searching = False
                st.session_state.search_stopped = True
                st.warning("⏹️ Search stopped by user")
                st.rerun()
        
        # Main content area - Search
        if search_button:
            if not keyword:
                st.error("Please enter a search keyword")
                return
            
            if not os.path.exists(directory):
                st.error(f"Directory not found: {directory}")
                return
            
            st.session_state.searching = True
            st.session_state.search_stopped = False
            
            try:
                # Get files
                files = get_all_files(directory, file_types)
                
                if not files:
                    st.error("No supported files found in directory")
                    st.session_state.searching = False
                    return
                
                # Pre-extraction if enabled
                if use_preextract and current_settings.cache.enabled:
                    with st.spinner(f"📤 Pre-extracting text from {len(files)} files..."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def extract_progress(current, total, filename):
                            progress = current / total
                            progress_bar.progress(progress)
                            status_text.text(f"Extracting: {filename} ({current}/{total})")
                        
                        extractor = TextExtractor(
                            cache=st.session_state.text_cache,
                            max_workers=current_settings.performance.max_workers
                        )
                        
                        extracted = extractor.extract_all(files, extract_progress)
                        st.session_state.extracted_texts = extracted
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        st.success(f"✅ Extracted text from {len(extracted)} files!")
                
                # Perform search
                with st.spinner("🔍 Searching documents in parallel..."):
                    manager = SearchManager()
                    st.session_state.search_manager = manager
                    
                    # Progress display
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_progress(current, total, filename):
                        if not manager.stop_requested:
                            progress = current / total
                            progress_bar.progress(progress)
                            status_text.text(f"Searching: {filename} ({current}/{total})")
                    
                    # Search with parallel processing
                    results = manager.search_directory(
                        directory=directory,
                        keyword=keyword,
                        case_sensitive=False,
                        whole_word=whole_word,
                        file_extensions=file_types,
                        progress_callback=update_progress
                    )
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Get completion statistics
                    completed, total = manager.get_completion_stats(len(files))
                    st.session_state.completion_stats = (completed, total)
                    
                    # Process results to merge nearby matches
                    if results:
                        processor = ResultProcessor()
                        processed_results = processor.process_results(results)
                        st.session_state.processed_results = processed_results
                    else:
                        st.session_state.processed_results = {}
                    
                    st.session_state.search_results = results
                    st.session_state.searching = False
                    
                    # Show completion message
                    if manager.stop_requested:
                        st.warning(f"⏹️ Search stopped. Showing results from {completed} files.")
                    else:
                        # Show cache stats if enabled
                        if st.session_state.text_cache:
                            cache_stats = st.session_state.text_cache.get_stats()
                            st.success(f"✅ Search completed! Found matches in {len(results)} files. "
                                     f"(Cache: {cache_stats['entries']} files, {cache_stats['size_mb']:.1f} MB)")
                        else:
                            st.success(f"✅ Search completed! Found matches in {len(results)} files.")
                    
                    # Highlight documents if requested
                    if auto_highlight and results and not manager.stop_requested:
                        with st.spinner("✨ Generating highlighted documents..."):
                            highlighter = DocumentHighlighter(manager)
                            highlighted = highlighter.highlight_all_results(
                                results, keyword, False
                            )
                            st.session_state.highlighted_files = highlighted
                    
            except Exception as e:
                st.error(f"Error during search: {str(e)}")
                st.session_state.searching = False
                import traceback
                st.code(traceback.format_exc())
                return
        
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
                
                # Results by file (using merged results)
                for file_path, merged_matches in processed_results.items():
                    total_matches_in_file = sum(m.match_count for m in merged_matches)
                    
                    with st.expander(
                        f"📄 {Path(file_path).name} ({total_matches_in_file} matches on {len(merged_matches)} page{'s' if len(merged_matches) != 1 else ''})", 
                        expanded=False
                    ):
                        st.caption(f"**Path:** {file_path}")
                        st.caption(f"**Size:** {get_file_size(file_path)}")
                        
                        st.markdown("### Matches")
                        
                        # Display merged matches
                        for idx, merged in enumerate(merged_matches, 1):
                            st.markdown(f"**Page {merged.page_number}** ({merged.match_count} match{'es' if merged.match_count > 1 else ''})")
                            
                            # Build highlighted context
                            context = merged.merged_context
                            highlighted_html = build_highlighted_html(
                                context, 
                                merged.match_positions
                            )
                            
                            # Display with black text
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
                        
                        # Download highlighted file
                        if st.session_state.highlighted_files and file_path in st.session_state.highlighted_files:
                            highlighted_path = st.session_state.highlighted_files[file_path]
                            
                            if os.path.exists(highlighted_path):
                                with open(highlighted_path, 'rb') as f:
                                    st.download_button(
                                        label="📥 Download Highlighted Document",
                                        data=f,
                                        file_name=Path(highlighted_path).name,
                                        mime="application/octet-stream",
                                        key=f"download_{file_path}",
                                        use_container_width=True
                                    )
                
                # Export results to Excel
                st.markdown("---")
                st.subheader("📊 Export Results")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if st.button("📥 Export to Excel", use_container_width=True):
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
                                use_container_width=True
                            )
                
                with col2:
                    st.info("💡 **Tip:** The Excel report contains all individual matches. The display above shows merged contexts for easier reading.")
    
    # ==================== TAB 2: SETTINGS ====================
    with tab2:
        render_settings_tab()


if __name__ == "__main__":
    main()
    