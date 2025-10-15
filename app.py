"""Streamlit application for Document Keyword Search Tool"""

import streamlit as st
import pandas as pd
from pathlib import Path
import os
from core.search_manager import SearchManager
from core.highlighter import DocumentHighlighter
from config import Config
from utils.helpers import get_file_size

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


def main():
    """Main application"""
    
    # Header
    st.title(f"{Config.PAGE_ICON} Document Keyword Search Tool")
    st.markdown("Search for keywords across PDF, DOCX, and DOC files with automatic highlighting")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
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
            st.warning("⏹️ Search stopped by user")
            st.rerun()
    
    # Main content area
    if search_button:
        if not keyword:
            st.error("Please enter a search keyword")
            return
        
        if not os.path.exists(directory):
            st.error(f"Directory not found: {directory}")
            return
        
        st.session_state.searching = True
        
        # Perform search
        with st.spinner("🔍 Searching documents..."):
            try:
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
                
                results = manager.search_directory(
                    directory=directory,
                    keyword=keyword,
                    case_sensitive=False,  # Always case insensitive
                    whole_word=whole_word,
                    file_extensions=file_types,
                    progress_callback=update_progress
                )
                
                progress_bar.empty()
                status_text.empty()
                
                st.session_state.search_results = results
                st.session_state.searching = False
                
                # Highlight documents if requested
                if auto_highlight and results and not manager.stop_requested:
                    with st.spinner("✨ Generating highlighted documents..."):
                        highlighter = DocumentHighlighter(manager)
                        highlighted = highlighter.highlight_all_results(
                            results, keyword, False
                        )
                        st.session_state.highlighted_files = highlighted
                
                if manager.stop_requested:
                    st.warning("⏹️ Search was stopped before completion")
                
            except Exception as e:
                st.error(f"Error during search: {str(e)}")
                st.session_state.searching = False
                return
    
    # Display results
    if st.session_state.search_results is not None:
        results = st.session_state.search_results
        
        if not results:
            st.info("🔍 No matches found for the given keyword")
        else:
            # Summary metrics
            total_matches = sum(len(matches) for matches in results.values())
            total_files = len(results)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📄 Files with Matches", total_files)
            col2.metric("🎯 Total Matches", total_matches)
            col3.metric("🔍 Search Term", f'"{keyword}"')
            
            st.markdown("---")
            
            # Results by file
            for file_path, matches in results.items():
                with st.expander(f"📄 {Path(file_path).name} ({len(matches)} matches)", expanded=False):
                    st.caption(f"**Path:** {file_path}")
                    st.caption(f"**Size:** {get_file_size(file_path)}")
                    
                    st.markdown("### Matches")
                    
                    # Display all matches for this file
                    for idx, match in enumerate(matches, 1):
                        st.markdown(f"**Match {idx} - Page {match.page_number}**")
                        
                        # Highlight the keyword in context with BLACK text
                        context = match.context
                        before = context[:match.match_start]
                        keyword_text = context[match.match_start:match.match_end]
                        after = context[match.match_end:]
                        
                        # Updated styling with black text
                        st.markdown(
                            f'<div style="background-color: #f8f9fa; padding: 12px; border-radius: 5px; '
                            f'margin: 8px 0; border-left: 3px solid #007bff; color: #000000; '
                            f'font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif;">'
                            f'<span style="color: #000000;">{before}</span>'
                            f'<span style="background-color: #FFFF00; font-weight: bold; '
                            f'padding: 2px 4px; border-radius: 2px; color: #000000;">{keyword_text}</span>'
                            f'<span style="color: #000000;">{after}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        
                        if idx < len(matches):
                            st.markdown("<div style='margin: 5px 0;'></div>", unsafe_allow_html=True)
                    
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
                    for file_path, matches in results.items():
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
                st.info("💡 **Tip:** The Excel report contains all matches with their context and page numbers for easy reference.")


if __name__ == "__main__":
    main()
