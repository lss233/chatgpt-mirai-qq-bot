"""Query classes for structured store indices."""

from llama_index.indices.query.struct_store.sql import (
    GPTNLStructStoreIndexQuery,
    GPTSQLStructStoreIndexQuery,
)

__all__ = ["GPTNLStructStoreIndexQuery", "GPTSQLStructStoreIndexQuery"]
