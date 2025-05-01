import os, threading
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from openai import OpenAI
from google.cloud import translate_v2 as translate
from google.cloud import speech

# 設定環境
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai_client = OpenAI(api_key=os.getenv('API_KEY'))

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-translate-key.json"
translate_client = translate.Client()
speech_client = speech.SpeechClient()

app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK', 200  # ⏱️ 快速回應 LINE Webhook

# 🔄 把處理事件的內容放在 background thread
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    threading.Thread(target=process_text_message, args=(event,)).start()

def process_text_message(event):
    user_text = event.message.text.strip()

    # Apple Flex Message
    if user_text.lower() == "apple":
        # [保持原本 Flex Message 略去]
        return

    if user_text.lower() == "選擇輸入語言":
        # [保持原本 Quick Reply 略去]
        return

    if user_text.startswith("輸入語言:"):
        # [略去]
        return

    if user_text.startswith("翻譯:"):
        # 翻譯內容處理
        try:
            target_language = "en"
            if "日文" in user_text:
                target_language = "ja"
            elif "韓文" in user_text:
                target_language = "ko"
            text_to_translate = user_text.replace("翻譯:", "").strip()
            result = translate_client.translate(text_to_translate, target_language=target_language)
            translated = result['translatedText']
        except Exception as e:
            translated = f"⚠️ 翻譯失敗：{str(e)}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated))
        return

    # 回應 GPT
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

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


@handler.add(MessageEvent, message=AudioMessage)
def handle_audio(event):
    threading.Thread(target=process_audio_message, args=(event,)).start()

def process_audio_message(event):
    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        with open('audio.mp3', 'wb') as f:
            for chunk in message_content.iter_content():
                f.write(chunk)

        with open("audio.mp3", "rb") as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MP3,
            sample_rate_hertz=16000,
            language_code="en-US"
        )
        response = speech_client.recognize(config=config, audio=audio)

        if response.results:
            user_text = response.results[0].alternatives[0].transcript
        else:
            user_text = "無法識別語音"

        translated_text = translate_client.translate(user_text, target_language='zh-TW')['translatedText']
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))

    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"⚠️ 語音處理失敗：{str(e)}"))

if __name__ == "__main__":
    app.run(port=8080)