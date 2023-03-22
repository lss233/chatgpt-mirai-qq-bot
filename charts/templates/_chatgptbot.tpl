{{- define "chatgptbot" }}
[openai]
[[openai.accounts]]
mode = "browserless"
# 你的 OpenAI access_token，登录后访问`https://chat.openai.com/api/auth/session`获取
access_token = "{{ .Values.chatgptbot.access_token }}"
puid = "{{ .Values.chatgptbot.puid }}"
# 如果你在国内，需要配置代理
# proxy="http://127.0.0.1:1080"

# 使用 ChatGPT Plus（plus 用户此项设置为 true）
paid = {{ .Values.chatgptbot.paid }}
title_pattern="qq-{session_id}"

auto_remove_old_conversations = true

[bing]
[[bing.accounts]]
cookie_content = "{{ .Values.bing.cookie_content }}"

[bard]
[[bard.accounts]]
cookie_content = "{{ .Values.bard.cookie_content }}"


[text_to_image]
# 文字转图片
always = false
default = false
font_size = 30 # 字体大小
width = 700  # 图片宽度
font_path = "fonts/sarasa-mono-sc-regular.ttf"  # 字体
offset_x = 50  # 起始点 X
offset_y = 50 # 起始点 Y

[trigger]
# 配置机器人要如何响应，下面所有项均可选 (也就是可以直接删掉那一行)

# 符合前缀才会响应，可以自己增减
prefix = [ "",]
prefix_friend = [ "x",]
prefix_group = [ "",]

prefix_ai = { "chatgpt-web" = ["gpt"], "bing-c" = ["bing"] }

# AI 画图的前缀
# 需要有 OpenAI 的 api_key 才能使用
prefix_image = ["画", "看"]
# 配置群里如何让机器人响应，"at" 表示需要群里 @ 机器人，"mention" 表示 @ 或者以机器人名字开头都可以，"none" 表示不需要
require_mention = "at"

# 重置会话的命令
reset_command = [ "重置会话",]

# 回滚会话的命令
rollback_command = [ "回滚会话",]

[response]
# 匹配指令成功但没有对话内容时发送的消息
placeholder = "您好！我是 Assistant，一个由 OpenAI 训练的大型语言模型。我不是真正的人，而是一个计算机程序，可以通过文本聊天来帮助您解决问题。如果您有任何问题，请随时告诉我，我将尽力回答。\n如果您需要重置我们的会话，请回复`重置会话`。"

# 发生错误时要发送的消息
error_format = "出现故障！如果这个问题持续出现，请和我说“重置会话” 来开启一段新的会话，或者发送 “回滚对话” 来回溯到上一条对话，你上一条说的我就当作没看见。\n{exc}"

# 是否要回复触发指令的消息
quote = true

# 发送下面那个提醒之前的等待时间
timeout = 30.0

# 超过响应时间时要发送的提醒
timeout_format = "我还在思考中，请再等一下~"

# 重置会话时发送的消息
reset = "会话已重置。"

# 回滚成功时发送的消息
rollback_success = "已回滚至上一条对话，你刚刚发的我就忘记啦！"

# 回滚失败时发送的消息
rollback_fail = "回滚失败，没有更早的记录了！"

# 服务器提示 429 错误时的回复
request_too_fast = "当前正在处理的请求太多了，请稍等一会再发吧！"

# 等待处理的消息的最大数量，如果要关闭此功能，设置为 0
max_queue_size = 10

# 队列满时的提示
queue_full = "抱歉！我现在要回复的人有点多，暂时没有办法接收新的消息了，请过会儿再给我发吧！"

# 新消息加入队列会发送通知的长度最小值
queued_notice_size = 3

# 新消息进入队列时，发送的通知。 queue_size 是当前排队的消息数
queued_notice = "消息已收到！当前我还有{queue_size}条消息要回复，请您稍等。"

[system]
# 是否自动同意进群邀请
accept_group_invite = {{ .Values.chatgptbot.accept_group_invite}}

# 是否自动同意好友请求
accept_friend_request = {{ .Values.chatgptbot.accept_friend_request}}

[presets]
# 切换预设的命令： 加载预设 猫娘
command = "加载预设 (\\w+)"

loaded_successful = "预设加载成功！"

[presets.keywords]
# 预设关键词 <-> 实际文件
"正常" = "presets/default.txt"
"猫娘" = "presets/catgirl.txt"
"香草" = "presets/xiangcao.txt"

[telegram]
bot_token = "{{ .Values.telegram.bot_token }}"

[discord]
bot_token = "{{ .Values.discord.bot_token }}"
{{- end }}