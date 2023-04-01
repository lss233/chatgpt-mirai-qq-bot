from llama_index import (
    GPTKeywordTableIndex,
    SimpleDirectoryReader,
    LLMPredictor,
    ServiceContext,
    GPTTreeIndex,
    GPTSimpleVectorIndex, 
    GithubRepositoryReader,
    GPTListIndex,
)
from langchain import OpenAI
from langchain.chat_models import ChatOpenAI
import os
import nest_asyncio

llm_predictor = LLMPredictor(llm=ChatOpenAI(temperature=0.7, model_name="gpt-4", max_tokens=4000))
service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)
index = GPTSimpleVectorIndex.load_from_disk('./merge_index.json', service_context=service_context)

prompts = [
    '''我在最后一步启动Mirai滑动输入之后，出现了Login failed: Error(bot=Bot(344061), code=45, title=禁止登录, message=登录失败，建议升级最新版本后重试，或通过问题反馈与我们联系。, errorInfo=)
2023-03-31 22:02:38 I/Bot.3441822061: Bot cancelled: Bot closed
2023-03-31 22:02:38 E/console: net.mamoe.mirai.network.WrongPasswordException: Error(bot=Bot(344061), code=45, title=禁止登录, message=登录失败，建议升级最新版本后重试，或通过问题反馈与我们联系。, errorInfo=)，是哪里出现了什么问题吗？''',
    '切换预设的指令是什么？',
    '我开了gpt plus，怎样才能在gpt4打开的情况下,还是用默认的gpt3.5模型，用gpt4需要自己切换',
    '请问ChatGPT 的 browserless 接入点 有搭建教程么？',
    'go-cqhttp可以设置两个反向 Universal 地址吗',
    '机器人为什么只回复私信，不在群聊里回复？',
    '机器人可以设定使用2个chatgpt-web的账户，一个用gpt3.5模型，一个用gpt4，这样的来回切换吗？',
    '我想要注释掉和QQ接收和发送的消息相关的log',
    '配置文件里有一行“metion表示机器人名字开头都可以“，这里的机器人名字指的是机器人昵称还是上面prefix配置的前缀？',
    '配置文件里的timeout的单位是什么'
]

for prompt in prompts:
    result = f"{index.query(prompt, verbose=False)}"
    print(f"ask: {prompt}  \n\nanswer:{result}\n===================\n")



'''
===================
ask: 我在最后一步启动Mirai滑动输入之后，出现了Login failed: Error(bot=Bot(344061), code=45, title=禁止登录, message=登录失败，建议升级最新版本后重试，或通过问题反馈与我们联系。, errorInfo=)
2023-03-31 22:02:38 I/Bot.3441822061: Bot cancelled: Bot closed
2023-03-31 22:02:38 E/console: net.mamoe.mirai.network.WrongPasswordException: Error(bot=Bot(344061), code=45, title=禁止登录, message=登录失败，建议升级最新版本后重试，或通过问题反馈与我们联系。, errorInfo=)，是哪里出现了什么问题吗？  
answer:从给出的信息来看，登录失败的原因是错误代码45，提示信息为“禁止登录，登录失败，建议升级最新版本后重试，或通过问题反馈与我们联系”。这可能是因为您使用的Mirai版本不是最新的，或者您的账号受到了某种限制。
要解决这个问题，您可以尝试以下方法：
1. 确保您使用的是Mirai的最新版本。升级到最新版本后，重新尝试登录。
2. 检查您的QQ账号是否有异常或者限制。如果有，尝试解决账号问题后重新登录。
3. 如果以上方法都无法解决问题，您可以通过问题反馈与Mirai的开发者联系，寻求帮助。
===================
ask: 切换预设的指令是什么？  
answer:抱歉，由于上下文信息不足，我无法提供切换预设的指令。请提供更多相关信息以便我为您解答。
===================
ask: 我开了gpt plus，怎样才能在gpt4打开的情况下,还是用默认的gpt3.5模型，用gpt4需要自己切换  
answer:在这个脚本中，GPT模型的版本是由`bot.py`文件决定的。要使用默认的gpt3.5模型，您需要确保`bot.py`文件中设置的模型是gpt3.5。如果您希望在gpt4打开的情况下仍然使用gpt3.5模型，可以在`bot.py`文件中添加一个选项来选择使用哪个模型。例如，您可以添加一个命令行参数或者在配置文件中设置模型版本。
如果要在运行时切换模型，您需要修改`bot.py`文件，添加一个切换模型的功能。这可能需要一些编程知识来实现。在实现这个功能后，您可以通过命令行参数或者配置文件来选择使用gpt3.5还是gpt4模型。
===================
ask: 请问ChatGPT 的 browserless 接入点 有搭建教程么？  
answer:在提供的上下文信息中，没有提到关于ChatGPT的browserless接入点搭建教程。但是，该项目提供了不同部署方式的教程，包括Linux、Windows和Mac系统。你可以查看上述教程部分以获取有关搭建和配置的详细信息。如果需要有关browserless接入点的搭建教程，建议查看项目的官方文档或者GitHub仓库以获得更多信息。
===================
ask: go-cqhttp可以设置两个反向 Universal 地址吗  
answer:是的，go-cqhttp 可以设置两个或多个反向 Universal 地址。您只需在`adapterSettings`的`reverse-ws`部分的`destinations`列表中添加多个地址即可。例如：
```yaml
adapterSettings:
  reverse-ws:
    destinations:
    - host: localhost
      port: 8554
      path: /
      protocol: ws
    - host: another.host
      port: 1234
      path: /another-path
      protocol: ws
```
在这个例子中，我们添加了两个反向 Universal 地址，一个在本地主机上的 8554 端口，另一个在另一个主机上的 1234 端口。这样，go-cqhttp 就可以与两个远端 websocket 服务器进行通信了。
===================
ask: 机器人为什么只回复私信，不在群聊里回复？  
answer:机器人在群聊里不回复的原因可能有以下几点：
1. 配置问题：请检查配置文件中关于群聊回复的设置，确保已经正确配置。
2. 权限问题：机器人可能没有足够的权限在群聊中回复，需要检查机器人在群里的权限设置。
3. 触发条件：机器人在群聊中可能需要特定的触发条件，如特定关键词或者@机器人，检查是否满足触发条件。
4. 网络或其他问题：机器人可能因为网络原因或其他错误导致无法在群聊中回复，请查看日志以获取详细信息。
如果以上方法都无法解决问题，请尝试查阅项目文档或者寻求开发者支持。
===================
ask: 机器人可以设定使用2个chatgpt-web的账户，一个用gpt3.5模型，一个用gpt4，这样的来回切换吗？  
answer:是的，机器人支持多账号功能。你可以在配置文件中设置多个 ChatGPT 账户，并分别指定使用不同的模型（例如 GPT-3.5 和 GPT-4）。在聊天过程中，可以通过相关命令或设置来切换不同账户和模型进行聊天。具体操作方法和命令可以参考项目文档和使用教程。
===================
ask: 我想要注释掉和QQ接收和发送的消息相关的log  
answer:在配置文件中找到与QQ接收和发送消息相关的log部分，然后在该部分的每一行开头添加 "#" 符号，这样就可以注释掉这部分内容。由于上下文信息中没有提供具体的QQ接收和发送消息相关的log部分，所以无法给出具体的代码示例。请在您的配置文件中查找相应的部分并按照上述方法进行注释。
===================
ask: 配置文件里有一行“metion表示机器人名字开头都可以“，这里的机器人名字指的是机器人昵称还是上面prefix配置的前缀？  
answer:这里的“机器人名字”应该指的是机器人的昵称。
===================
ask: 配置文件里的timeout的单位是什么  
answer:配置文件里的timeout的单位是秒。
===================
'''