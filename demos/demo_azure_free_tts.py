import sys
sys.path.append('../utils')


from azure_free_tts import azure_free_speech, mp3_to_silk
import os
import asyncio

async def main():
    binary_array = await azure_free_speech('你好世界！')
    # print(binary_array)
    path = os.getcwd() + "/1.mp3"
    print(path)
    silk = await mp3_to_silk(bytes(binary_array))
    with open(path, 'wb') as f:
        f.write(bytes(binary_array))

asyncio.run(main())
