from kirara_ai.workflow.core.block.registry import BlockRegistry


def create_test_block_registry() -> BlockRegistry:
    """创建一个用于测试的 BlockRegistry 实例"""
    registry = BlockRegistry()

    # 注册一些基本类型
    registry._type_system.register_type("str", str)
    registry._type_system.register_type("int", int)
    registry._type_system.register_type("float", float)
    registry._type_system.register_type("bool", bool)
    registry._type_system.register_type("list", list)
    registry._type_system.register_type("dict", dict)
    registry._type_system.register_type("Any", object)

    return registry 