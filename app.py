import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from openai import OpenAI
import requests
from datetime import datetime

# LINE 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
line_handler = WebhookHandler(LINE_CHANNEL_SECRET)

# OpenAI GPT 設定
openai_client = OpenAI(api_key=os.getenv('API_KEY'))

# 初始化 Flask
app = Flask(__name__)

# 使用 OpenWeatherMap API 來獲取天氣資訊
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')

# 使用貨幣兌換 API
EXCHANGE_RATE_API_KEY = os.getenv('EXCHANGE_RATE_API_KEY')

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
    user_text = event.message.text.strip().lower()

    # 行程安排與提醒
    if "行程" in user_text or "行程安排" in user_text:
        reply_text = "請提供您的旅遊行程，我將為您記錄並提醒。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    # 景點介紹與推薦
    elif "景點" in user_text or "推薦" in user_text:
        reply_text = "請告訴我您所在的城市或想要參觀的景點，並提供一些偏好，我會為您推薦。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    # 語言翻譯
    elif "翻譯" in user_text:
        text_to_translate = user_text.replace("翻譯", "").strip()
        # 假設 OpenAI GPT 也能進行簡單的翻譯處理
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是 LINE 機器人中的智慧助理"},
                    {"role": "user", "content": f"請將以下文字翻譯成中文：{text_to_translate}"}
                ]
            )
            reply_text = response.choices[0].message.content.strip()
        except Exception as e:
            reply_text = f"⚠️ 發生錯誤：{str(e)}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    # 當地天氣預報
    elif "天氣" in user_text:
        city = user_text.replace("天氣", "").strip()
        weather_info = get_weather(city)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=weather_info))
        return

    # 貨幣兌換率與匯率計算
    elif "匯率" in user_text:
        currency_info = get_exchange_rate()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=currency_info))
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


# 取得當地天氣資訊
def get_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=zh_tw"
        response = requests.get(url)
        data = response.json()

        if data["cod"] != 200:
            return f"❌ 無法取得 {city} 的天氣資料。"
        
        weather = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        return f"🌤 {city} 的天氣：{weather}，溫度：{temperature}°C"
    except Exception as e:
        return f"❌ 發生錯誤：{str(e)}"


# 取得匯率資訊
def get_exchange_rate():
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url)
        data = response.json()
        exchange_rate = data["rates"]["TWD"]
        return f"💰 目前的美元對台幣匯率為：1 USD = {exchange_rate} TWD"
    except Exception as e:
        return f"❌ 發生錯誤：{str(e)}"
