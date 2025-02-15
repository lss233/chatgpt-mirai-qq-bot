from setuptools import setup, find_packages

setup(
    name="chatgpt-mirai-http-legacy-adapter",
    version="1.0.0",
    description="HTTP legacy adapter plugin for ChatGPT-Mirai",
    author="Internal",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "requests"
    ],
    entry_points={
        "chatgpt_mirai.plugins": [
            "http_legacy = im_http_legacy_adapter.plugin:HttpLegacyAdapterPlugin"
        ]
    }
) 