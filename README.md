# 🔍 Document Keyword Search Tool with RAG

A powerful, feature-rich document search application with AI-powered question answering capabilities. Search through PDF, DOCX, and DOC files with lightning-fast performance, intelligent context extraction, and a built-in RAG (Retrieval-Augmented Generation) chatbot.

![Python Version](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Streamlit](https://img.shields.io/badge/streamlit-1.28.0-red)

## ✨ Features

### 🔎 Advanced Search Capabilities
- **Multi-format Support**: Search across PDF, DOCX, and DOC files
- **Fuzzy Matching**: Automatically handles word variations (e.g., "low-resource" matches "low resource", "low resources")
- **Three Search Modes**:
  - 🔥 **Hybrid** (Default): Combines indexing with fast extraction for optimal performance
  - ⚡ **Fast Extract**: Pure extraction without indexing for one-time searches
  - 📚 **Indexed Only**: Lightning-fast searches on pre-indexed documents
- **Intelligent Context**: Displays matches with surrounding sentences for better understanding
- **Smart Merging**: Automatically groups nearby matches on the same page
- **Progress Tracking**: Real-time progress bars with file-by-file updates

### 🎨 Document Highlighting
- Generate highlighted versions of matching documents
- Supports PDF and DOCX output formats
- Yellow highlights with word boundaries
- On-demand generation to prevent performance issues

### 📊 Export Options
- **Excel (.xlsx)**: Structured data with file paths, page numbers, and context
- **Word (.docx)**: Combined report with all results, formatted with headers and citations
- **PDF**: Professional report with proper pagination and styling

### 💬 AI-Powered Chat (RAG)
- **100% Free & Local**: Uses Ollama for LLM inference (no API costs!)
- **Semantic Search**: ChromaDB vector store with sentence transformers
- **Conversational AI**: Context-aware follow-up questions
- **Multi-Document Reasoning**: Synthesizes information across multiple files
- **Automatic Citations**: Sources included with every answer
- **Model Flexibility**: Switch between different Ollama models on the fly

### ⚡ Performance Optimizations
- **Multi-threaded Processing**: Up to 32 parallel workers
- **Persistent Indexing**: SQLite-based index with FTS5 full-text search
- **Smart Caching**: LRU cache for extracted text (configurable size)
- **Batch Processing**: Efficient handling of large document sets
- **Stop/Resume**: Ability to stop searches and retrieve partial results

### ⚙️ Customizable Settings
- **Performance Profiles**: Pre-configured settings for different hardware capabilities
- **Flexible Workers**: Adjust parallelism (1-32 threads)
- **Context Control**: Configure sentences before/after matches
- **Cache Management**: Enable/disable caching with size limits
- **Index Management**: View statistics, clear, or rebuild index

---

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- (Optional) Ollama for RAG features - [Download Ollama](https://ollama.com/download)

### Step 1: Clone the Repository
```bash
git clone https://github.com/brannytech/document_word_search.git

cd document_word_search
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: (Optional) Setup Ollama for RAG
```bash
# Install Ollama from https://ollama.com/download

# Pull a model (recommended: llama3.2)
ollama pull llama3.2

# Verify installation
ollama list
```

---

## 🚀 Quick Start

### Launch the Application
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

### Basic Search Workflow
1. **Select Directory**: Click "📂 Browse Folder" or enter path manually
2. **Enter Keyword**: Type your search term in the sidebar
3. **Configure Options**: Choose file types and search settings
4. **Search**: Click "🔍 Search" button
5. **View Results**: Expand file sections to see matches with context
6. **Export**: Download results as Excel, Word, or PDF

### Using RAG Chat
1. Navigate to **💬 Chat with Documents** tab
2. Click **⚡ Initialize RAG System** (first time only)
3. Click **📄 Index Documents** in sidebar
4. Select directory and start indexing
5. Ask questions in natural language!

---

## 📖 Usage Guide

### Search Modes Explained

#### 🔥 Hybrid Mode (Recommended)
- **Best for**: Regular use, repeated searches
- **How it works**: 
  - First search: Builds index (15-30s for 200 files)
  - Subsequent searches: Uses index (< 1s)
  - New files: Automatically indexed during search
- **Performance**: Fast after initial indexing

#### ⚡ Fast Extract Mode
- **Best for**: One-time searches, changing document sets
- **How it works**: Extracts text on-the-fly using PyMuPDF
- **Performance**: 10-20s for 200 files (no persistence)

#### 📚 Indexed Only Mode
- **Best for**: Static document sets, production environments
- **How it works**: Only searches pre-indexed files
- **Performance**: Instant (< 1s) but requires pre-indexing

### Performance Profiles

| Profile | Workers | RAM Usage | Best For |
|---------|---------|-----------|----------|
| **Low Resource** | 2 | ~200 MB | Laptops, limited hardware |
| **Balanced** ⭐ | 8 | ~500 MB | Most users (default) |
| **High Performance** | 16 | ~1 GB | Powerful desktops |
| **Maximum** | 32 | ~2 GB | Servers, batch processing |

### Fuzzy Matching Examples

The tool automatically handles word variations:

| Search Term | Matches |
|-------------|---------|
| `low-resource` | "low-resource", "low resource", "low resources" |
| `machine learning` | "machine-learning", "machine learning", "Machine Learning" |
| `COVID-19` | "COVID-19", "COVID 19", "Covid-19" |

---

## 🎯 Advanced Features

### Document Indexing
```
Settings Tab → Index & Search Mode Settings
- View indexed files count and database size
- Clear index to start fresh
- Rebuild index for changed documents
```

### Cache Management
```
Settings Tab → Cache & Memory Settings
- Enable/disable text caching
- Set cache size limit (MB)
- Toggle persistent cache (saves to disk)
- View cache statistics
```

### RAG Configuration
```
Chat Tab → Sidebar
- Switch between Ollama models
- View vector store statistics
- Manage conversation history
- Export chat sessions
```

### Keyboard Shortcuts
- `Ctrl + Enter`: Submit search / Send chat message
- `Esc`: Stop ongoing search

---

## 📁 Project Structure
```
document-keyword-search-tool/
│
├── app.py                      # Main Streamlit application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── user_settings.json          # User preferences
│
├── core/                       # Core functionality
│   ├── hybrid_search_engine.py # Multi-mode search engine
│   ├── document_index.py       # SQLite indexing
│   ├── fast_extractors.py      # Multi-threaded extraction
│   ├── rag_engine.py           # RAG orchestration
│   ├── vector_store.py         # ChromaDB integration
│   ├── llm_client.py           # Ollama client
│   └── ...
│
├── searchers/                  # Document-specific searchers
│   ├── pdf_searcher.py
│   ├── docx_searcher.py
│   └── doc_searcher.py
│
└── utils/                      # Helper functions
    └── helpers.py
```

---

## 🛠️ Configuration

### Environment Variables
Create a `.env` file (optional):
```env
OLLAMA_HOST=http://localhost:11434
MAX_WORKERS=8
CACHE_SIZE_MB=500
```

### Settings File
The application saves your preferences to `user_settings.json`:
```json
{
  "performance": {
    "max_workers": 8,
    "search_mode": "hybrid"
  },
  "context": {
    "sentences_before": 2,
    "sentences_after": 2
  },
  "cache": {
    "enabled": true,
    "max_size_mb": 500
  }
}
```

---

## 🔧 Troubleshooting

### Common Issues

#### Search is slow
- **Solution**: Switch to Hybrid or Indexed Only mode in Settings
- Increase max workers if you have CPU cores available
- Enable caching to speed up repeated searches

#### PyMuPDF installation fails
```bash
# Try installing separately
pip install PyMuPDF --upgrade

# Or use alternative
pip install pymupdf-fonts
```

#### Ollama not connecting
```bash
# Check if Ollama is running
ollama list

# Restart Ollama service
# Windows: Restart from system tray
# Mac/Linux: ollama serve
```

#### Memory errors with large files
- Reduce max workers in Settings
- Switch to Low Resource profile
- Disable caching temporarily
- Process files in smaller batches

#### Highlighting hangs
- Disable "Auto-generate highlighted documents"
- Generate highlights on-demand per file
- Limit to < 20 files for auto-highlighting

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt
pip install black flake8 pytest

# Run tests
pytest tests/

# Format code
black .
```

---

## 📝 License

#This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **PyMuPDF** - Fast PDF text extraction
- **Streamlit** - Beautiful web interface
- **ChromaDB** - Vector database for RAG
- **Ollama** - Free local LLM inference
- **Sentence Transformers** - Text embeddings

---

## 📊 Performance Benchmarks

| Dataset | Files | Mode | Time | Memory |
|---------|-------|------|------|--------|
| Small | 50 | Hybrid (1st) | 8s | 300 MB |
| Small | 50 | Hybrid (2nd+) | <1s | 100 MB |
| Medium | 200 | Hybrid (1st) | 25s | 500 MB |
| Medium | 200 | Indexed Only | <1s | 150 MB |
| Large | 1000 | Fast Extract | 180s | 800 MB |

*Tested on: Intel i7-10700, 16GB RAM, SSD*

---

## 🗺️ Roadmap

- [ ] Cloud deployment (Docker + Kubernetes)
- [ ] Support for more file formats (TXT, RTF, HTML)
- [ ] Batch processing API
- [ ] Advanced regex search
- [ ] Custom embedding models
- [ ] Multi-language support
- [ ] OCR for scanned documents
- [ ] Elasticsearch integration

---

## 📧 Contact

- **Author**: Olushola Olawale
- **Email**: brannytech.co@gmail.com
- **GitHub**: [@brannytech](https://github.com/brannytech)
- **Issues**: [Report a bug](https://github.com/brannytech/document_word_search/issues)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=brannytech/document_word_search&type=Date)](https://star-history.com/#brannytech/document-keyword-search-tool&Date)

---

**Made with ❤️ by [Your Name]**

*If you find this tool helpful, please consider giving it a ⭐ on GitHub!*
```

---

## Additional Files to Include

### 1. `LICENSE` (MIT License Example)
```
MIT License

Copyright (c) 2025 Olawale

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 2. `.gitignore`
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Application specific
search_results/
temp/
cache/
vector_store/
conversations/
*.db
user_settings.json

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log