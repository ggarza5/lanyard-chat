
import json
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from transformers import DistilBertTokenizer, DistilBertModel
from typing import Union
from langchain_core.runnables import RunnablePassthrough, chain
from utils.execute_query import execute_query
from llm.schema.faq_schema import Faq
from llm.model import gemini_chat_model
from llm.prompts.faq_prompt import faq_prompt
from sentence_transformers import SentenceTransformer

# Use DistilBERT for faster processing
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertModel.from_pretrained('distilbert-base-uncased')

# Cache for frequently asked queries (optional)
# faq_cache = {}

# Load a better model for embeddings
new_model = SentenceTransformer('all-MiniLM-L6-v2')

# # Function to embed a sentence using DistilBERT
# def embed_sentence(sentence):
#     inputs = tokenizer(sentence, return_tensors='pt', truncation=True, padding=True)
#     with torch.no_grad():
#         outputs = model(**inputs)
#     return outputs.last_hidden_state.mean(dim=1).numpy()

# Function to embed a sentence
def embed_sentence(sentence):
    return new_model.encode(sentence, convert_to_numpy=True)

def preprocess_text(text):
    return ' '.join(text.lower().strip().split())

# Precompute and store FAQ embeddings for faster query processing
def precompute_faq_embeddings(faq_data):
    for faq in faq_data:
        faq['question'] = preprocess_text(faq['question'])
        faq['embedding'] = embed_sentence(faq['question'])

# SQL Query to retrieve all FAQs and their precomputed embeddings
def get_all_faqs():
    sql_query = "SELECT id, question, answer FROM faq"
    result = execute_query(sql_query)
    faqs = [{'id': row['id'], 'question': row['question'], 'answer': row['answer']} for row in result]
    
    # Precompute embeddings for all FAQ questions
    precompute_faq_embeddings(faqs)
    
    return faqs

# Function to compute semantic similarity between the query and precomputed FAQ embeddings
def semantic_search(user_query: str, faq_data: list) -> list:
    query_embedding = embed_sentence(user_query)
    
    # Use precomputed embeddings for each FAQ
    faq_embeddings = [faq['embedding'] for faq in faq_data]
    
    # Compute cosine similarity between the query and FAQ embeddings
    similarities = [cosine_similarity(query_embedding.reshape(1, -1), faq_embedding.reshape(1, -1))[0][0] for faq_embedding in faq_embeddings]
    
    # Add similarity scores to FAQs for better debugging
    for i, faq in enumerate(faq_data):
        faq['similarity'] = similarities[i]
    # Sort FAQs by similarity score (highest first)
    # sorted_faqs = sorted(zip(similarities, faq_data), key=lambda x: x[0], reverse=True)

    # Sort FAQs by similarity score
    sorted_faqs = sorted(faq_data, key=lambda x: x['similarity'], reverse=True)

    # Debugging: Print top similarities
    print("Top Similarities:")
    for faq in sorted_faqs[:5]:  # Print top 5 matches
        print(f"Question: {faq['question']}, Similarity: {faq['similarity']}")
    
    # Define a similarity threshold to filter out irrelevant FAQs
    threshold = 0.5
    # relevant_faqs = [faq for similarity, faq in sorted_faqs if similarity > threshold]
    relevant_faqs = sorted_faqs[:1] if sorted_faqs and sorted_faqs[0]['similarity'] > 0.5 else []
    # Return top 1 most similar FAQ
    return relevant_faqs

# Check the cache for frequently asked queries (optional)
# def check_cache(user_query):
#     if user_query in faq_cache:
#         print(f"Fetching result from cache for query: {user_query}")
#         return faq_cache[user_query]
#     return None

# Store the result in cache (optional)
# def cache_result(user_query, result):
#     faq_cache[user_query] = result

# Transformation Layer: Transform the model output to match the Faq schema
def transform_result(relevant_faqs):
    if relevant_faqs:
        return {
            "message": relevant_faqs[0]["answer"],
            "has_answer": True,
            "link": None,
            "image": None,
            "type":"TEXT"
        }
    else:
        return {
            "message": "No relevant answer found.",
            "has_answer": False,
            "link": None,
            "image": None,
            "type":"TEXT"
        }

# Define the chain that retrieves FAQ data from the database and integrates with prompt template
@chain
def get_data(x):
    user_query = x["message"]
    
    # Check if the result is in the cache
    # cached_result = check_cache(user_query)
    # if cached_result:
    #     return cached_result
    
    # Get all FAQs from the SQL database with precomputed embeddings
    all_faqs = get_all_faqs()

    # Perform semantic search to find relevant FAQs
    relevant_faqs = semantic_search(user_query, all_faqs)
    
    # Cache the result for future queries (optional)
    # cache_result(user_query, relevant_faqs)
    print("Transform FAQS:", transform_result(relevant_faqs))
    # Transform the result into a structure expected by Faq schema
    # Transform the result
    result = transform_result(relevant_faqs)
    
    # Wrap the result in a RunnablePassthrough-compatible format
    return {"faq": result}

# Define the default chain, which retrieves the data and processes it with the FAQ model
default_chain = (
    RunnablePassthrough().assign(
        context=get_data
    )
    # | faq_prompt
    # | gemini_chat_model.with_structured_output(Faq)
)

# Correct input format
input_data = {
    "message": "How do I reset my password?"
}

# Run the chain with the correct input
result = default_chain.invoke(input=input_data)

# Output the result directly (it's already a dictionary)
print(result)

