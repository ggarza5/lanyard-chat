from langchain_core.runnables import chain
from typing import Union, Dict, Any

@chain
def response_chain(x: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    results = x.get('decision', {})
    if results:
        result_type = results.get("type", "")
        if result_type == "TEXT":
            answer = results.get('message', "I'm sorry, I don’t have that info right now.")
            link = results.get('link', "")
            return {"type": "faq", "data": answer, "link": link}
        elif result_type == "PRODUCT":
            return {"type": "product", "data": results}
        else:
            return {"type": "unavailable", "data": "I'm sorry, I don’t have that info right now."}
    
    return None
