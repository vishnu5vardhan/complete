#!/usr/bin/env python3

import faiss
import pickle
from typing import List, Dict
from sentence_transformers import SentenceTransformer

# Load index and metadata once
index = None
metadata = None

def load_resources():
    """Load FAISS index and metadata if not already loaded"""
    global index, metadata
    if index is None or metadata is None:
        print("Loading resources...")
        index = faiss.read_index("embeddings/creditcard.index")
        with open("embeddings/creditcard_metadata.pkl", "rb") as f:
            metadata = pickle.load(f)
        print(f"Loaded index with {index.ntotal} vectors and {len(metadata)} metadata entries")

def search_creditcards(user_query: str) -> List[Dict]:
    """
    Search for credit cards that match the user query
    
    Args:
        user_query: A string describing what the user is looking for
        
    Returns:
        List of dictionaries containing the top 6 matching credit card metadata
    """
    # Make sure resources are loaded
    load_resources()
    
    # Load model and encode query
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_embedding = model.encode([user_query])[0].reshape(1, -1).astype('float32')
    
    # Perform similarity search
    k = 6  # Number of results to return
    distances, indices = index.search(query_embedding, k)
    
    # Retrieve full metadata for matching products
    results = [metadata[idx] for idx in indices[0]]
    
    return results

def main():
    """Test the search functionality with a sample query"""
    # Sample query
    user_query = "Best credit card for dining and online shopping"
    
    print(f"Searching for: {user_query}")
    results = search_creditcards(user_query)
    
    print(f"\nTop 6 results for: {user_query}")
    for i, card in enumerate(results):
        print(f"\n{i+1}. {card['loan_product_name']} - {card['lender_name']}")
        print(f"   Type: {card['loan_type']}")
        print(f"   Features: {card['features_list']}")
        print(f"   Suitable for: {card['loan_purpose_suitability']}")

if __name__ == "__main__":
    main() 