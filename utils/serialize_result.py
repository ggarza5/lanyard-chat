from datetime import datetime

def serialize_result(result):
    for item in result:
        for key, value in item.items():
            if isinstance(value, datetime):
                item[key] = value.isoformat()
    return result
