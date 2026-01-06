import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
import json

class VectorClient:
    _instance = None
    _emb_fn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Connect once
        if not hasattr(self, 'client'):
            self.client = chromadb.HttpClient(host='localhost', port=8001)
            # Use a lightweight local embedding model - CACHED at class level
            if VectorClient._emb_fn is None:
                print("DEBUG: Loading SentenceTransformer model (One-time)...")
                VectorClient._emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            
            self.collection_name = "dataset_embeddings"

    def _get_collection(self):
        return self.client.get_or_create_collection(
            name=self.collection_name, 
            embedding_function=VectorClient._emb_fn
        )

    def index_dataset(self, dataset_name, df: pd.DataFrame, tags: list = None):
        """
        Convert each row of a dataframe into a searchable document in ChromaDB
        """
        documents = []
        metadatas = []
        ids = []

        # Index up to 100 rows for better search coverage
        sample_df = df.head(100)
        
        # Prepare tag string for document enrichment
        tags_str = ""
        if tags and len(tags) > 0:
            tags_str = f" [Tags: {', '.join(tags)}]"
        
        for i, row in sample_df.iterrows():
            # Create a text representation of the row including TAGS
            doc_text = f"Dataset: {dataset_name}{tags_str} | " + " | ".join([f"{col}: {val}" for col, val in row.items()])
            documents.append(doc_text)
            
            meta = {"source": dataset_name, "row_index": i}
            # Store tags in metadata for filtering if needed
            if tags:
                meta["tags"] = ",".join(tags)
                
            metadatas.append(meta)
            ids.append(f"{dataset_name}_{i}")

        if documents:
            collection = self._get_collection()
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            return len(documents)
        return 0

    def search(self, query, n_results=5):
        collection = self._get_collection()
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
