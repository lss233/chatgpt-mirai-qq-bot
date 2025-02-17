from setuptools import find_packages, setup

setup(
    name="chatgpt-mirai-wecom-adapter",
    version="1.0.0",
    description="WeCom adapter plugin for ChatGPT-Mirai",
    author="Internal",
    packages=find_packages(),
    install_requires=["wechatpy", "pycryptodome"],
    entry_points={
        "chatgpt_mirai.plugins": ["wecom = im_wecom_adapter.plugin:WeComAdapterPlugin"]
    },
)
