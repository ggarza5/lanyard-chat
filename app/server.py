import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langserve import add_routes
from llm.chain.full_chain import full_chain

app = FastAPI()

class QueryInput(BaseModel):
    message: str
    customer_id: Optional[str] = None  # Add customer_id to the model

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

add_routes(app, full_chain, path='/full')

@app.post("/query")
async def query(input: QueryInput):
    try:
        print(input.message, 'mess')
        # Prepare parameters for `full_chain.invoke`
        params = {"message": input.message}
        if input.customer_id:
            params["customer_id"] = input.customer_id
        # print(input.customer_id, 'customer_id')
        result = await asyncio.to_thread(full_chain.invoke, params)
        # result = full_chain.invoke({"message": input.message, "customer_id": input.customer_id})

        return {"result": result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
