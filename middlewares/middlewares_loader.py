import os
import inspect
import importlib
from loguru import logger

def load_middlewares(middlewares_dir='./middlewares'):
    middlewares = []

    # 遍历middlewares目录下的所有.py文件
    for filename in os.listdir(middlewares_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # 去掉.py后缀
            module = importlib.import_module(f'middlewares.{module_name}')

            # 遍历模块中的所有类
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    if 'middleware' in name.lower() and name != 'Middleware':
                        # 检查类是否有指定的方法
                        methods = ['handle_request', 'handle_respond', 'on_respond', 'handle_respond_completed']
                        if any(hasattr(obj, method) for method in methods):
                            logger.debug(f'加载中间件 {name}')
                            middlewares.append(obj())

    return middlewares
