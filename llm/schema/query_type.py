from langchain_core.pydantic_v1 import BaseModel, Field

class QueryType(BaseModel):
    type: str = Field(description="product for product-related queries, faq for FAQs")
