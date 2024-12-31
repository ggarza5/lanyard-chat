import json
from langchain_core.runnables import chain
from llm.chain.sub_chain.default_chain import default_chain

@chain
def chat_chain(x):
    message = x["message"]
    print('chat,',x)
    result = default_chain.invoke(input={"message": message})
    return result
    #json.loads(result.json())
