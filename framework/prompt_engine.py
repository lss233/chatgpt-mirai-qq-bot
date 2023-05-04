import inspect
import re
from typing import Dict, Optional, Callable
from typing import List

import yaml
from charset_normalizer import from_bytes
from pydantic import BaseModel, Extra
from loguru import logger
import json

from framework.prompt import evaluate_expression


class PromptFlowUnsupportedException(Exception):
    pass


class PromptActionNotFoundException(Exception):
    pass


class ActionArgsBaseModel(BaseModel):
    class Config:
        extra = Extra.allow


class ActionBlockBaseModel(BaseModel):
    action: str
    args: ActionArgsBaseModel = ActionArgsBaseModel()
    name: Optional[str]
    output: Optional[str]
    when: Optional[str]
    fail_continue: bool = True
    retry: int = 3


class PromptFlowBaseModel(BaseModel):
    name: str
    author: str
    supported_llms: List[str] = []
    init: List['ActionBlockBaseModel'] = []
    input: List['ActionBlockBaseModel'] = []
    output: List['ActionBlockBaseModel'] = []


def load_prompt(file_path: str) -> PromptFlowBaseModel:
    with open(file_path, "rb") as f:
        if guessed_str := from_bytes(f.read()).best():
            return PromptFlowBaseModel.parse_obj(yaml.safe_load(str(guessed_str)))
        else:
            raise ValueError("无法识别配置文件，请检查是否输入有误！")


def get_variable_value(variables, variable_name):
    parts = variable_name.split(".")
    value = variables
    for part in parts:
        if part in value:
            value = value[part]
        else:
            return None
    return value


def set_variable_value(variables, variable_name, value):
    parts = variable_name.split(".")
    if len(parts) == 1:
        variables[variable_name] = value
    else:
        variable = parts[0]
        if variable in variables:
            value_dict = variables[variable]
            attribute_path = parts[1:]
            for attribute in attribute_path[:-1]:
                if attribute not in value_dict:
                    value_dict[attribute] = {}
                value_dict = value_dict[attribute]
            value_dict[attribute_path[-1]] = value


def replace_variables(string, variables):
    pattern = r"\$\{\{\s*(\w+(\.\w+)*)\s*\}\}"
    for match in re.findall(pattern, string):
        variable_name = match[0]
        value = get_variable_value(variables, variable_name)
        if value is not None:
            string = string.replace(f"${{{{ {variable_name} }}}}", str(value))
    return string


async def execute_action_block(action_flow: List[ActionBlockBaseModel], context: Dict[str, str],
                               actions: Dict[str, Callable]):
    for block in action_flow:
        if block.action not in actions:
            raise PromptActionNotFoundException(block.action)
        action_callable = actions[block.action]

        # 跳过不满足的情况
        if block.when and not evaluate_expression(block.when, context):
            continue

        params = inspect.signature(action_callable).parameters

        args = {}

        for key, value in block.args.dict().items():
            if isinstance(value, str):
                if variable := get_variable_value(context, value):
                    args[key] = variable
                else:
                    args[key] = replace_variables(value, context)
            elif params[key].annotation != inspect.Parameter.empty and isinstance(value, dict):
                args[key] = params[key].annotation(**value)
            else:
                args[key] = value

        for i in range(block.retry + 1):
            try:
                result = action_callable(**args)
                if result and inspect.iscoroutine(result):
                    result = await result

                if block.name:
                    context[block.name] = result

                if block.output:
                    set_variable_value(context, block.output, result)

                logger.debug(
                    f"[Prompt execution] completed \naction: {block.action}, \nname: {block.name}, \nresult: {result}")
                break
            except Exception as e:
                logger.exception(e)
                logger.error(f"[Prompt execution] failed\naction: {block.action}, \nname:{block.name}")
                if i == block.retry and not block.fail_continue:
                    raise e
