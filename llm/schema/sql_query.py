from langchain_core.pydantic_v1 import BaseModel, Field

class SqlQuery(BaseModel):
    "Create a sql query"
    query: str = Field(description="SQL query based on the input")
