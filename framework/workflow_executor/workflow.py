from typing import List

from .block import Block

class Workflow:
    def __init__(self, blocks: List['Block'], wires: List['Wire']):
        self.blocks = blocks
        self.wires = wires

class Wire:
    def __init__(self, source_block: 'Block', source_output: str, target_block: 'Block', target_input: str):
        self.source_block = source_block
        self.source_output = source_output
        self.target_block = target_block
        self.target_input = target_input