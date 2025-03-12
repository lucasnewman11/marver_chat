import os
from dotenv import load_dotenv
from llama_index.embeddings.voyageai import VoyageEmbedding

# Load environment variables
load_dotenv()

# Set up Voyage embeddings with the provided key
voyage_api_key = "pa-Hj2UDd0uOnPfrSlYLyfka-XlM859rV4MWwx8B-5YAOM"
embed_model = VoyageEmbedding(
    voyage_api_key=voyage_api_key,
    model_name="voyage-3",
    input_type="search_query"
)

def test_voyage_embeddings():
    """Test Voyage AI embeddings"""
    print("Testing Voyage AI embeddings...")
    
    try:
        # Generate a test embedding
        test_text = "Hello VoyageAI!"
        embeddings = embed_model.get_text_embedding(test_text)
        
        # Print information about the embedding
        print(f"✅ Successfully generated embeddings with Voyage AI")
        print(f"Embedding length: {len(embeddings)}")
        print(f"First 5 values: {embeddings[:5]}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to generate embeddings: {str(e)}")
        return False

if __name__ == "__main__":
    test_voyage_embeddings()