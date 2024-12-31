import json
from typing import Union, Dict, Any
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from llm.model import gemini_chat_model
from langchain_core.runnables import chain
from llm.chain.sub_chain.chat_chain import chat_chain
from llm.chain.sub_chain.product_chain import product_chain
from llm.schema.query_type import QueryType
from llm.prompts.query_type import query_prompt
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAI
from llm.model import gemini_generative_model
import os

# Define the prediction chain
predict_chain = query_prompt | gemini_chat_model.with_structured_output(QueryType)
# Available chains dictionary
chains = {
    "faq": chat_chain
}

llm = GoogleGenerativeAI(model="gemini-pro", temperature=0)
def get_dynamic_sql_prompt() -> str:
    system_instructions = """
    Type of messages:
    --------------------------------
    Product:
    Description: All information related to product and user order will comes under this. This includes features, pricing, availability, order summary, etc.
    Examples: What are the products/lanyard/lanyards?
    Where can I find products/lanyards?
    What is the price of the product/lanyard?
    What is my last order?
    what is my first order?
    show me orders from last week.

    FAQ:
    Description: Frequently asked question about the company, products or lanyards will comes under this. Include query related to quotation, extra charges
    Examples: Can i place my order online?
    What are custom lanyards?
    When will my order arrive?
    when will i receive my custom lanyard?
    How to place an order?
    What is return policy?
    What's the turnaround time?
    What imprint methods do you offer?
    What is the minimum order quantity?
    what is the thickness of your lanyard?
    What lanyard options do you have?
    How do I get a lanyard?
    Can I order a single custom lanyard?
    What are lanyards used for?
    What are the standard sizes for custom lanyards?
    What options do you have?

    Greetings:
    Description: If user query includes only greeting like "hi", "hello", "hey", "greetings", "what's up", "howdy"
    ----------------------------------


    With the information provided, together with the examples and previous context, determine which type are these messages belong to.
    You can choose only 1 type
    Output ONLY "FAQ", "Product" or Greeting.
    """
    return system_instructions

def create_dynamic_sql_prompt(user_query: str) -> ChatPromptTemplate:
    dynamic_prompt = get_dynamic_sql_prompt()
    return ChatPromptTemplate.from_messages([
                ("system", dynamic_prompt),
                ("human", user_query)
            ])

# classify_chain = classify_dynamic_prompt | gemini_generative_model

# Initialize session store if needed for session-specific data
session_store = {}

@chain
def decision_chain(x: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    try:
        # Extract and sanitize user query
        user_query = x.get("message", "").strip().lower()
        classify_dynamic_prompt = create_dynamic_sql_prompt(user_query)
        classify_chain = classify_dynamic_prompt | gemini_generative_model
        classification = classify_chain.invoke(input={"user_query": user_query})
        print("Received query and classification:", user_query, classification)  # Debugging input query

        # Check if query starts with "need" to decide which chain to run
        if classification == "FAQ":
            print("Running FAQ chain only")  # Log specific chain use
            result = chat_chain.invoke(x)
            faq = result.get("context").get("faq", "No relevant FAQ found.")  # Run only product_chain
            faq_link = os.getenv('DOMAIN_FE').strip().rstrip('/')
            # Directly return the result
            if faq.get("has_answer") == True:
                return {
                    "type": "TEXT",
                    "message": faq.get("message", "No relevant FAQ found."),
                    "has_answer": faq.get("has_answer",False),
                    "link": ""
                }
            return {
                    "type": "TEXT",
                    "message": ("I'm sorry, I don’t have that info right now."),
                    "has_answer": faq.get("has_answer",False),
                    "link": faq_link.rstrip('/')+"#faqSection"
                }
        elif classification == "Product":
            print("Running Product chain")  # Log product chain execution
            result = product_chain.invoke(x)  # Instantiate and invoke product_chain
            print("result Product chain", result)
            if isinstance(result, dict):
                return {
                    "type": "PRODUCT",
                    "message": result.get("message", "No relevant Product found."),
                    "has_answer": result.get("has_answer",False),
                    "image": result.get("image", ""),
                    "link": result.get("link", "")
                }
            return {
                     "type": "PRODUCT",
                    "message": ("Sorry! couldn't find the product you're looking for, please checkout our product page from below link."),
                    "has_answer": False,
                    "image": "",
                    "link": f"{os.getenv('DOMAIN_FE')}/collections/no-sidebar"
                }
        else :
            return {
                "message": f"Hello! How can I assist you today?",
                "link": None,
                "image": None,
                "type":"TEXT"
                }

        print("Result:", result)  # Output the result for debugging
        return None

    except Exception as e:
        print("Error in decision_chain:", e)  # Log the error
        raise  # Re-raise the exception for visibility in server logs
