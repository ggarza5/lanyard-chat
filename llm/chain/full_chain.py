from typing import Optional
from langchain_core.runnables import RunnablePassthrough
from langserve import CustomUserType
from operator import itemgetter
from llm.chain.response_chain import response_chain
from llm.chain.understand_chain import decision_chain

class Input(CustomUserType):
    message: str
    customer_id: Optional[str] = None  # Add customer_id to the Input class

# Define the full_chain
full_chain = (
    RunnablePassthrough().with_types(input_type=Input)
    | {
        # Pass both message and customer_id through to the next stage
        "message": lambda input: input["message"],
        "customer_id": lambda input: input.get("customer_id", None),  # Safely handle optional customer_id
    }
    |
    RunnablePassthrough().assign(
        decision=decision_chain
    )
    |
    RunnablePassthrough().assign(
        response=response_chain
    )
    |
    {
        "message": itemgetter("message"),
        "response": itemgetter("response"),
        "customer_id": lambda input: input.get("customer_id", None),
    }
)
