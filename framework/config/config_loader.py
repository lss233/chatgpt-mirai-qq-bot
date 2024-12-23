from ruamel.yaml import YAML
from pydantic import BaseModel, ValidationError
from typing import Type

class ConfigLoader:
    """
    配置文件加载器，支持加载和保存 YAML 文件，并保留注释。
    """

    yaml = YAML()

    @staticmethod
    def load_config(config_path: str, config_class: Type[BaseModel]) -> BaseModel:
        """
        从 YAML 文件中加载配置，并将其序列化为相应的配置对象。
        :param config_path: 配置文件路径。
        :param config_class: 配置文件类。
        :return: 配置对象。
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = ConfigLoader.yaml.load(f)
            return config_class(**config_data)
        except ValidationError as e:
            raise ValueError(f"配置文件验证失败: {e}")
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}")

    @staticmethod
    def save_config(config_path: str, config_object: BaseModel):
        """
        将配置对象保存到 YAML 文件中，并保留注释。
        :param config_path: 配置文件路径。
        :param config_object: 配置对象。
        """
        with open(config_path, "w", encoding="utf-8") as f:
            ConfigLoader.yaml.dump(config_object.dict(), f)