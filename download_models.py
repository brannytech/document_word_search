"""Download required models before running the app"""

print("=" * 60)
print("Downloading RAG System Models")
print("=" * 60)

# 1. Download embedding model
print("\n📦 Downloading embedding model (all-MiniLM-L6-v2)...")
print("This is a one-time download (~90MB)")
print("Please wait...\n")

try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Embedding model downloaded successfully!")
except Exception as e:
    print(f"❌ Error downloading embedding model: {e}")
    print("\nTry installing manually:")
    print("pip install sentence-transformers")

# 2. Check Ollama
print("\n🤖 Checking Ollama...")
try:
    import ollama
    models = ollama.list()
    model_names = [m['name'] for m in models.get('models', [])]
    
    if model_names:
        print(f"✅ Ollama is running. Available models: {model_names}")
    else:
        print("⚠️ Ollama is running but no models found.")
        print("Run: ollama pull llama3.2")
except Exception as e:
    print(f"⚠️ Ollama not available: {e}")
    print("Install from: https://ollama.com/download")
    print("Then run: ollama pull llama3.2")

print("\n" + "=" * 60)
print("✨ Setup complete! You can now run: streamlit run app.py")
print("=" * 60)