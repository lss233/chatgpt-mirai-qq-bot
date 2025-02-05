from setuptools import setup, find_packages

setup(
    name="chatgpt-mirai-telegram-adapter",
    version="1.0.0",
    description="Telegram adapter plugin for ChatGPT-Mirai",
    author="Internal",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot",
        "telegramify-markdown"
    ],
    entry_points={
        "chatgpt_mirai.plugins": [
            "telegram = im_telegram_adapter.plugin:TelegramAdapterPlugin"
        ]
    }
) 