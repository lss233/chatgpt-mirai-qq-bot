"""Query classes for tree indices."""

from llama_index.indices.query.tree.embedding_query import GPTTreeIndexEmbeddingQuery
from llama_index.indices.query.tree.leaf_query import GPTTreeIndexLeafQuery
from llama_index.indices.query.tree.retrieve_query import GPTTreeIndexRetQuery

__all__ = [
    "GPTTreeIndexLeafQuery",
    "GPTTreeIndexRetQuery",
    "GPTTreeIndexEmbeddingQuery",
]
