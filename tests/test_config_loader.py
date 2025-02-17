import unittest
from unittest.mock import mock_open, patch

from pydantic import BaseModel

from framework.config.config_loader import ConfigLoader


class TestConfig(BaseModel):
    __test__ = False
    """测试用配置类"""
    name: str
    value: int


class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self.test_config = TestConfig(name="test", value=123)
        self.test_config_path = "test_config.yaml"

    def test_save_config_with_backup(self):
        """测试保存配置文件时的备份功能"""
        # Mock os.path.exists 返回 True,表示配置文件存在
        with patch("os.path.exists", return_value=True) as mock_exists:
            # Mock shutil.copy2 用于验证备份操作
            with patch("shutil.copy2") as mock_copy:
                # Mock open 和 yaml.dump 操作
                mock_file = mock_open()
                with patch("builtins.open", mock_file):
                    with patch.object(ConfigLoader.yaml, "dump") as mock_dump:
                        # 执行保存操作
                        ConfigLoader.save_config_with_backup(
                            self.test_config_path, self.test_config
                        )

                        # 验证是否检查了文件存在
                        mock_exists.assert_called_once_with(self.test_config_path)

                        # 验证是否创建了备份
                        mock_copy.assert_called_once_with(
                            self.test_config_path, f"{self.test_config_path}.bak"
                        )

                        # 验证是否打开了文件进行写入
                        mock_file.assert_called_with(
                            self.test_config_path, "w", encoding="utf-8"
                        )

                        # 验证是否调用了 yaml.dump
                        mock_dump.assert_called_once_with(
                            self.test_config.model_dump(), mock_file()
                        )

    def test_save_config_without_backup(self):
        """测试当配置文件不存在时的保存操作(不应创建备份)"""
        # Mock os.path.exists 返回 False,表示配置文件不存在
        with patch("os.path.exists", return_value=False) as mock_exists:
            # Mock shutil.copy2 用于验证备份操作
            with patch("shutil.copy2") as mock_copy:
                # Mock open 和 yaml.dump 操作
                mock_file = mock_open()
                with patch("builtins.open", mock_file):
                    with patch.object(ConfigLoader.yaml, "dump") as mock_dump:
                        # 执行保存操作
                        ConfigLoader.save_config_with_backup(
                            self.test_config_path, self.test_config
                        )

                        # 验证是否检查了文件存在
                        mock_exists.assert_called_once_with(self.test_config_path)

                        # 验证没有创建备份
                        mock_copy.assert_not_called()

                        # 验证是否打开了文件进行写入
                        mock_file.assert_called_with(
                            self.test_config_path, "w", encoding="utf-8"
                        )

                        # 验证是否调用了 yaml.dump
                        mock_dump.assert_called_once_with(
                            self.test_config.model_dump(), mock_file()
                        )


if __name__ == "__main__":
    unittest.main()
