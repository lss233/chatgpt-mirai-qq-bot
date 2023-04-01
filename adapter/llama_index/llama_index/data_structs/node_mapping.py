"""Node mapping."""

from typing import Dict, Type
from llama_index.data_structs.node_v2 import Node, ImageNode, IndexNode, NodeType


TYPE_TO_NODE: Dict[str, Type[Node]] = {
    NodeType.TEXT: Node,
    NodeType.IMAGE: ImageNode,
    NodeType.INDEX: IndexNode,
}
