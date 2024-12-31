from langchain_core.prompts import ChatPromptTemplate

template = """
You are a question classification system. Your task is to determine the type of the question based on the following categories:

- 'product' for questions specifically related to detailed product inquiries about lanyards (e.g., Nylon colored lanyards, 3-inch lanyards).
- 'faq' for general inquiries or FAQ-type questions, or if the question is not related to lanyards (e.g.,lanyard materials, lanyard sizes, order policies, minimum order quantities, shipping details, contact information, company-related information).

Question: {question}

Please follow these instructions:
- If the question is specifically about a particular lanyard, classify it as 'product'.
- If the question is not related to lanyards or is a general inquiry, classify it as 'faq'.

Format your response as a JSON object with a single key 'type' containing either 'product' or 'faq'.
Ensure that the response is in JSON format and includes only the required key-value pair.
"""

query_prompt = ChatPromptTemplate.from_template(template=template)
