from setuptools import setup, find_packages

setup(
    name="chatgpt-mirai-llm-presets",
    version="1.0.0",
    description="Preset LLM adapters for ChatGPT-Mirai",
    author="Internal",
    packages=find_packages(),
    install_requires=[
        "openai",
        "google-generativeai",
        "anthropic",
        "requests"
    ],
    entry_points={
        "chatgpt_mirai.plugins": [
            "llm_presets = llm_preset_adapters.plugin:LLMPresetsPlugin"
        ]
    }
) 