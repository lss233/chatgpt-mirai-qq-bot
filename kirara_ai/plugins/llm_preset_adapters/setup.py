from setuptools import find_packages, setup

setup(
    name="kirara_ai-llm-presets",
    version="1.0.0",
    description="Preset LLM adapters for kirara_ai",
    author="Internal",
    packages=find_packages(),
    install_requires=["openai", "google-generativeai", "anthropic", "requests"],
    entry_points={
        "chatgpt_mirai.plugins": [
            "llm_presets = llm_preset_adapters.plugin:LLMPresetsPlugin"
        ]
    },
)
