import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from openai import OpenAI

# LINE 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
line_handler = WebhookHandler(LINE_CHANNEL_SECRET)

# OpenAI GPT 設定
openai_client = OpenAI(api_key=os.getenv('API_KEY'))

# 初始化 Flask
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "✅ LINE Bot on Vercel is running."

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    print("📩 Received callback from LINE")
    print("📦 Body:", body)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid Signature")
        abort(400)

    return 'OK'

@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("✅ webhook message received")
    process_text_message(event)

def process_text_message(event):
    user_text = event.message.text.strip()

    if user_text == "排行榜":
        reply_text = "📊 此功能尚未完善，敬請期待後續更新！"
    else:
        # OpenAI GPT 回覆
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是 LINE 機器人中的智慧助理"},
                    {"role": "user", "content": user_text}
                ]
            )
            reply_text = response.choices[0].message.content.strip()
        except Exception as e:
            reply_text = f"⚠️ 發生錯誤：{str(e)}"

    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
    except Exception as e:
        print("⚠️ 回覆訊息失敗：", e)


# 本地測試
if __name__ == "__main__":
    app.run(port=8080)
