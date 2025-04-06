#!/usr/bin/env python3

import os
import pandas as pd
import pickle
from sentence_transformers import SentenceTransformer
import faiss
from tqdm import tqdm

def main():
    # Create embeddings directory if it doesn't exist
    os.makedirs("embeddings", exist_ok=True)
    
    print("Loading credit card data...")
    # Load credit card data
    df = pd.read_csv("/Users/vishn/Desktop/llm_recommender/data/creditcard.csv")
    
    print("Generating product descriptions...")
    # Generate product descriptions by combining relevant fields
    fields = [
        "loan_product_name",
        "lender_name",
        "loan_type",
        "features_list",
        "loan_purpose_suitability",
        "application_process_channels",
        "other_details"
    ]
    
    # Fill NA values with empty strings
    for field in fields:
        df[field] = df[field].fillna("")
    
    # Combine fields to create product descriptions
    product_descriptions = df[fields].agg(" ".join, axis=1).tolist()
    
    print("Loading SentenceTransformer model...")
    # Load the sentence transformer model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    print("Encoding product descriptions...")
    # Encode descriptions into embeddings with progress bar
    embeddings = model.encode(product_descriptions, show_progress_bar=True, convert_to_numpy=True)
    
    print("Creating FAISS index...")
    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    print("Saving FAISS index...")
    # Save FAISS index
    faiss.write_index(index, "embeddings/creditcard.index")
    
    print("Saving product metadata...")
    # Save product metadata as a list of dictionaries
    metadata = df.to_dict(orient="records")
    with open("embeddings/creditcard_metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)
    
    print("Done! Index and metadata saved to embeddings folder.")

if __name__ == "__main__":
    main() 