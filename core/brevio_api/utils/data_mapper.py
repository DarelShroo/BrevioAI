from typing import Optional, Type, TypeVar

T = TypeVar("T")


def generate_obj_if_data_exist(data: Optional[dict], obj: Type[T]) -> Optional[T]:
    if data:
        return obj(**data)
    return None
