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
    
    print("Loading loan data...")
    # Load loan data with error handling for inconsistent CSV format
    try:
        # Try with more flexible parsing options
        df = pd.read_csv("/Users/vishn/Desktop/llm_recommender/data/loan_dataset.csv", 
                          engine='python',  # Use the python engine which is more flexible
                          error_bad_lines=False,  # Skip bad lines
                          warn_bad_lines=True,    # Warn about bad lines
                          on_bad_lines='skip',    # Skip bad lines
                          quoting=3,              # No special quoting
                          escapechar='\\',        # Use backslash as escape character
                          low_memory=False)       # Disable low memory warnings
    except Exception as e:
        print(f"Error loading CSV with flexible options: {e}")
        print("Trying with more basic approach...")
        # If that fails, try reading as a plain text file and splitting manually
        with open("/Users/vishn/Desktop/llm_recommender/data/loan_dataset.csv", 'r') as f:
            lines = f.readlines()
        
        # Get headers from first line
        headers = lines[0].strip().split(',')
        
        # Create an empty list to store data
        data = []
        
        # Process each line after the header
        for line in lines[1:]:
            # Remove newline and split by comma
            values = line.strip().split(',')
            
            # Create a dictionary mapping headers to values
            # Use only as many values as there are headers
            row_dict = {headers[i]: values[i] if i < len(values) else "" 
                      for i in range(len(headers))}
            
            data.append(row_dict)
        
        # Create DataFrame from the list of dictionaries
        df = pd.DataFrame(data)
    
    print(f"Successfully loaded data with {len(df)} rows and {len(df.columns)} columns")
    
    print("Generating product descriptions...")
    # Get all available fields
    all_fields = df.columns.tolist()
    
    # Fill NA values with empty strings for all fields
    for field in all_fields:
        df[field] = df[field].fillna("")
    
    # Combine all fields to create comprehensive product descriptions
    product_descriptions = df.apply(lambda row: ' '.join(str(val) for val in row), axis=1).tolist()
    
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
    faiss.write_index(index, "embeddings/loan.index")
    
    print("Saving product metadata...")
    # Save product metadata as a list of dictionaries
    metadata = df.to_dict(orient="records")
    with open("embeddings/loan_metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)
    
    print("Done! Index and metadata saved to embeddings folder.")

if __name__ == "__main__":
    main() 