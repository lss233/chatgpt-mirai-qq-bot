from setuptools import find_packages, setup

setup(
    name="kirara_ai-http-legacy-adapter",
    version="1.0.0",
    description="HTTP legacy adapter plugin for kirara_ai",
    author="Internal",
    packages=find_packages(),
    install_requires=["aiohttp", "requests"],
    entry_points={
        "chatgpt_mirai.plugins": [
            "http_legacy = im_http_legacy_adapter.plugin:HttpLegacyAdapterPlugin"
        ]
    },
)
