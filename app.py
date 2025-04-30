import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage,
    QuickReply, QuickReplyButton, AudioMessage
)
from openai import OpenAI
from google.cloud import translate_v2 as translate  # Google Translate
from google.cloud import speech  # Google Speech-to-Text

# LINE BOT 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# OpenAI GPT 設定 
openai_client = OpenAI(api_key=os.getenv('API_KEY'))

# Google Translate 設定 
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-translate-key.json"
translate_client = translate.Client()

# Google Speech-to-Text 設定
speech_client = speech.SpeechClient()  # Google Speech-to-Text 初始化

# 初始化 Flask
app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()

    # Apple Flex Message 回覆
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
        line_bot_api.reply_message(event.reply_token, flex_message)
        return

    # 步驟 1：讓使用者選擇輸入語言（來源語言）
    if user_text.lower() == "選擇輸入語言":
        quick_reply_message = TextSendMessage(
            text="請選擇您要輸入的語言",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action={"type": "message", "label": "中文", "text": "輸入語言: 中文"}),
                    QuickReplyButton(action={"type": "message", "label": "英文", "text": "輸入語言: 英文"}),
                    QuickReplyButton(action={"type": "message", "label": "日文", "text": "輸入語言: 日文"})
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, quick_reply_message)
        return

    # 步驟 2：讓使用者選擇翻譯成的語言（目標語言）
    if user_text.startswith("輸入語言:"):
        user_language = user_text.replace("輸入語言:", "").strip()

        quick_reply_message = TextSendMessage(
            text=f"您選擇了 {user_language}，請選擇您要翻譯的語言。",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action={"type": "message", "label": "翻譯成英文", "text": "翻譯: 你好"}),
                    QuickReplyButton(action={"type": "message", "label": "翻譯成日文", "text": "翻譯: こんにちは"}),
                    QuickReplyButton(action={"type": "message", "label": "翻譯成韓文", "text": "翻譯: 안녕하세요"})
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, quick_reply_message)
        return

    # 翻譯功能：處理翻譯
    if user_text.startswith("翻譯:"):
        text_to_translate = user_text.replace("翻譯:", "").strip()

        # 根據用戶選擇的語言進行翻譯
        target_language = "en"  # 預設翻譯成英文
        if "日文" in text_to_translate:
            target_language = "ja"
        elif "韓文" in text_to_translate:
            target_language = "ko"

        try:
            result = translate_client.translate(text_to_translate, target_language=target_language)
            translated = result['translatedText']
        except Exception as e:
            translated = f"⚠️ 翻譯失敗：{str(e)}"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated))
        return

    # 如果使用者選擇語音訊息
    if isinstance(event.message, AudioMessage):
        # 下載語音並保存為 MP3 文件
        message_content = line_bot_api.get_message_content(event.message.id)
        with open('audio.mp3', 'wb') as f:
            for chunk in message_content.iter_content():
                f.write(chunk)

        # 使用 Google Speech-to-Text 將語音轉換為文字
        with open("audio.mp3", "rb") as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MP3,
            sample_rate_hertz=16000,
            language_code="en-US"  # 預設語言是英文，根據需求修改
        )

        # 發送音訊資料進行語音識別
        response = speech_client.recognize(config=config, audio=audio)

        # 假設語音識別結果是「Hello world」
        if response.results:
            user_text = response.results[0].alternatives[0].transcript
        else:
            user_text = "無法識別語音"

        # 使用 Google Translate 進行翻譯
        translated_text = translate_client.translate(user_text, target_language='zh-TW')['translatedText']

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))
        return

    # 回應 OpenAI GPT 回覆（如果無法識別文字）
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

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(port=8080)

