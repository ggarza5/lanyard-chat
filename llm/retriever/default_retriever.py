import os
from dotenv import load_dotenv

load_dotenv()

from langchain_pinecone import PineconeVectorStore
from llm.model import gemini_embedding_model

default_vector_store = PineconeVectorStore.from_existing_index(
    index_name=os.environ['PINECONE_FAQ_INDEX'],
    embedding= gemini_embedding_model,
)

default_retriever=default_vector_store.as_retriever()

