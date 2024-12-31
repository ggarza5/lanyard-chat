import os
from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings, GoogleGenerativeAI
from langchain_groq import ChatGroq


gemini_chat_model = ChatGoogleGenerativeAI(
    model="gemini-pro",
    api_key=os.environ["GOOGLE_API_KEY"],
    temperature=0
    )

gemini_embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

gemini_generative_model = GoogleGenerativeAI(
    model="gemini-pro",
    api_key=os.environ["GOOGLE_API_KEY"],
    temperature=0
    )

groq_mixtral_model = ChatGroq(
    temperature=0,
    model_name="mixtral-8x7b-32768",
    api_key=os.environ["GROQ_API_KEY"]
    )