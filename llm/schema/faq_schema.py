from langchain_core.pydantic_v1 import BaseModel, Field

class Faq(BaseModel):
    "JSON Object with answer to the user question and a boolean value to show if the context has the answer"
    answer: str = Field(description="Return a shortened answer if the context has the users questions and answer")
    has_answer: bool = Field(description="Boolean value to indicate if the user question is answered or not")
