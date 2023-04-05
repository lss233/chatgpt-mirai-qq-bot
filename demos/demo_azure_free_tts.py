import sys
sys.path.append('../utils')


from azure_free_tts import azure_free_speech, mp3_to_silk
import os
import asyncio

async def main():
    path = os.getcwd() + "/1.wav"
    if await azure_free_speech('你好世界！我是微软Abc', 'zh-CN-XiaoyiNeural', path):
    # print(binary_array)
        print(path)
    else:
        print('null')

asyncio.run(main())
