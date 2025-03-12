# Embedding model options for the Sales Call Simulator
# Use this as a reference to change embeddings in app.py if needed

# Option 1: Voyage AI (default in our app)
# Excellent quality but requires API key
from llama_index.embeddings import VoyageEmbeddings

embed_model = VoyageEmbeddings(
    voyage_api_key="your_voyage_api_key",
    voyage_model="voyage-2"  # or "voyage-large-2" for higher quality
)

# Option 2: OpenAI Embeddings
# Good quality, requires OpenAI API key
from llama_index.embeddings import OpenAIEmbedding

embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",  # or "text-embedding-3-large" for higher quality
    api_key="your_openai_api_key"
)

# Option 3: HuggingFace Embeddings
# Runs locally, free, but requires more RAM/CPU
from llama_index.embeddings import HuggingFaceEmbedding

embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"  # Good balance of quality and speed
)

# Option 4: Cohere Embeddings
# Good quality, requires Cohere API key
from llama_index.embeddings import CohereEmbedding

embed_model = CohereEmbedding(
    api_key="your_cohere_api_key",
    model_name="embed-english-v3.0"
)

# To update the app, replace the embedding model in app.py:
# 1. Import the appropriate embedding class
# 2. Replace the existing embed_model initialization in init_llama_index()
# 3. Update requirements.txt if needed
# 4. Update secrets.toml to include the relevant API key