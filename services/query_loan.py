#!/usr/bin/env python3

import os
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
        try:
            if not os.path.exists("embeddings/loan.index"):
                raise FileNotFoundError("FAISS index file not found at embeddings/loan.index")
            index = faiss.read_index("embeddings/loan.index")
            
            if not os.path.exists("embeddings/loan_metadata.pkl"):
                raise FileNotFoundError("Metadata file not found at embeddings/loan_metadata.pkl")
            with open("embeddings/loan_metadata.pkl", "rb") as f:
                metadata = pickle.load(f)
                
            print(f"Loaded index with {index.ntotal} vectors and {len(metadata)} metadata entries")
        except Exception as e:
            print(f"Error loading resources: {e}")
            raise

def search_loans(user_query: str) -> List[Dict]:
    """
    Search for loans that match the user query
    
    Args:
        user_query: A string describing what the user is looking for
        
    Returns:
        List of dictionaries containing the top 6 matching loan metadata
    """
    # Make sure resources are loaded
    load_resources()
    
    # Load model and encode query
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_embedding = model.encode([user_query])[0].reshape(1, -1).astype('float32')
    
    # Perform similarity search
    top_k = 6  # Number of results to return
    distances, indices = index.search(query_embedding, top_k)
    
    # Retrieve full metadata for matching products
    results = [metadata[idx] for idx in indices[0]]
    
    return results

def main():
    """Test the search functionality with a sample query"""
    # Sample query
    user_query = "Looking for a low interest personal loan with no prepayment charges"
    
    print(f"Searching for: {user_query}")
    try:
        results = search_loans(user_query)
        
        print(f"\nTop 6 results for: {user_query}")
        for i, loan in enumerate(results):
            print(f"\n{i+1}. {loan['loan_product_name']} - {loan['lender_name']}")
            print(f"   Type: {loan['loan_type']}")
            print(f"   Features: {loan['features_list']}")
            
        # Print in the requested format
        print("\nSimple format:")
        for loan in results:
            print(loan["loan_product_name"], "-", loan["features_list"])
            
    except Exception as e:
        print(f"Error during search: {e}")

if __name__ == "__main__":
    main() 