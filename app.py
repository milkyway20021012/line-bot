import os, threading
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
    threading.Thread(target=process_text_message, args=(event,)).start()

def process_text_message(event):
    user_text = event.message.text.strip()

    if user_text.lower() == "apple":
        flex_message = FlexSendMessage(
            alt_text='Apple 商店選單',
            contents={
                "type": "bubble",
                "hero": {
                    "type": "image",
                    "url": "https://help.apple.com/assets/67E1D466D1A1E142910B49DB/67E1D46AE03ADF0486097DE7/zh_TW/cfef5ce601689564e0a39b4773f20815.png",
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#FFFFFF",
                    "contents": [
                        {
                            "type": "text",
                            "text": "Apple Store",
                            "weight": "bold",
                            "size": "xl",
                            "align": "center"
                        },
                        {
                            "type": "text",
                            "text": "立即探索最新 Apple 產品",
                            "size": "sm",
                            "color": "#888888",
                            "wrap": True,
                            "align": "center"
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#000000",
                            "action": {
                                "type": "uri",
                                "label": "前往 Apple 官網",
                                "uri": "https://www.apple.com/tw/"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                                "type": "uri",
                                "label": "探索 Mac 系列",
                                "uri": "https://www.apple.com/tw/mac/"
                            }
                        }
                    ]
                }
            }
        )
        try:
            line_bot_api.reply_message(event.reply_token, flex_message)
        except Exception as e:
            print("⚠️ 回覆 Flex Message 失敗：", e)
        return

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
        print("⚠️ 回覆 GPT 訊息失敗：", e)

# 本地測試
if __name__ == "__main__":
    app.run(port=8080)

# Vercel 專用
handler = app