import os
from dotenv import load_dotenv

load_dotenv()

from langchain_pinecone import PineconeVectorStore
from llm.model import gemini_embedding_model

products_vector_store = PineconeVectorStore.from_existing_index(
    index_name=os.environ['PINECONE_PRODUCTS_INDEX'],
    embedding= gemini_embedding_model,
)

products_retriever=products_vector_store.as_retriever()
