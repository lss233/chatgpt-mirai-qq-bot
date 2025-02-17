from typing import Any, Optional


class Input:
    def __init__(
        self,
        name: str,
        label: str,
        data_type: type,
        description: str,
        nullable: bool = False,
        default: Optional[Any] = None,
    ):
        self.name = name
        self.label = label
        self.data_type = data_type
        self.description = description
        self.nullable = nullable
        self.default = default

    def validate(self, value: Any) -> bool:
        if value is None:
            return self.nullable
        return isinstance(value, self.data_type)


class Output:
    def __init__(self, name: str, label: str, data_type: type, description: str):
        self.name = name
        self.label = label
        self.data_type = data_type
        self.description = description

    def validate(self, value: Any) -> bool:
        return isinstance(value, self.data_type)
