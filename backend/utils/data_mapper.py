from typing import Optional

@staticmethod
def generate_obj_if_data_exist(data: Optional[dict], obj: type) -> Optional[object]:
    if data:
        return obj(**data)
    return None