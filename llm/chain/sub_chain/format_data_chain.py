from llm.model import gemini_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

template = """
Question: {message}\n

Context: \n{data}\n

Based on the context, please answer the question:\n

If you cannot find an answer, please respond with: "I'm sorry, but I couldn't find an answer."

"""

prompt = ChatPromptTemplate.from_template(template)

format_data_chain = (
      prompt
    | gemini_chat_model
    | StrOutputParser()
)
