from typing import Optional


class ParamMeta:
    def __init__(self, label: Optional[str] = None, description: Optional[str] = None):
        self.label = label
        self.description = description

    def __repr__(self):
        return f"ParamMeta(label={self.label}, description={self.description})"

    def __str__(self):
        return self.__repr__()
