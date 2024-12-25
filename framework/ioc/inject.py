from functools import wraps
from inspect import signature
from typing import Any, Callable, Optional, Type


from framework.ioc.container import DependencyContainer

def get_all_attributes(cls):
    if not hasattr(cls, '__annotations__'):
        return {}
    attributes = dict(cls.__annotations__.items())
    # 获取父类的属性和方法
    for base in cls.__bases__:
        attributes.update(get_all_attributes(base))

    return attributes


class Inject:
    def __init__(self, container: Any = None):
        self.container = container  # 允许外部传入 container
        
    def create(self, target: type):
        # 注入类
        injected_class = self.__call__(target)
        # 注入构造函数
        return self.inject_function(injected_class)
    
    def __call__(self, target: Any):
        # 如果修饰的是一个类
        if isinstance(target, type):
            return self.inject_class(target)
        # 如果修饰的是一个函数
        elif isinstance(target, Callable):
            return self.inject_function(target)
        # 如果修饰的是一个属性
        elif isinstance(target, property):
            return self.inject_property(target)
        else:
            raise TypeError("Inject can only be used on classes, functions, or properties.")

    def inject_class(self, cls: Type):
        # 遍历类的属性，尝试注入依赖
        for name, injecting_type in get_all_attributes(cls).items():
            attr = getattr(cls, name) if hasattr(cls, name) else None
            setattr(cls, name, self.inject_property(name, cls, injecting_type, attr))
        return cls
    def inject_function(self, func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数的参数签名
            sig = signature(func)
            # 检查是否有 DependencyContainer 对象作为参数传递进来
            container_param = self.find_container(args, kwargs)
            # 如果有 DependencyContainer 对象，则将其作为 self.container
            if container_param:
                self.container = container_param

            # 遍历参数，注入依赖
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            for name, param in sig.parameters.items():
                if param.annotation != param.empty and name not in kwargs and self.container:
                    bound_args.arguments[name] = self.container.resolve(param.annotation)

            # 调用实际的函数
            return func(*bound_args.args, **bound_args.kwargs)

        return wrapper

    def inject_property(self, name, cls, injecting_type, prop: Optional[property]):
        # 获取 property 的 fget, fset, fdel
        if prop:
            fget = prop.fget or (lambda self: None)
            fset = prop.fset or (lambda self, value: None)
            fdel = prop.fdel or (lambda self: None)
        else:
            fget = lambda self: None
            fset = lambda self, value: None
            fdel = lambda self: None
            
        # 为 property 的 fget 注入依赖
        @wraps(fget)
        def new_fget(_self):
            # 获取 property 的返回值
            if self.container and isinstance(injecting_type, type):
                # 如果返回值是一个类型，尝试从 container 中解析
                return self.container.resolve(injecting_type)
            raise ValueError(f"Type object {cls} has no attribute {name}")

        # 返回新的 property
        return property(new_fget, fset, fdel)

    def find_container(self, args, kwargs):
        # 检查是否有 DependencyContainer 对象作为参数传递进来
        for arg in args:
            if isinstance(arg, DependencyContainer):
                return arg
        for key, value in kwargs.items():
            if isinstance(value, DependencyContainer):
                return value
        return None
