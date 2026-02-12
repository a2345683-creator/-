import os
import random
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 設定金鑰
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 從本地 JSON 讀取資料 ---
def get_random_law():
    try:
        # 讀取剛剛建立的 laws.json
        with open('laws.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 隨機抽取一條
        target = random.choice(data)
        
        # 產出完美的排版
        result = [
            "📖 【刑法抽抽抽】",
            f"\n📌 {target['no']}",
            f"\n{target['content']}",
            "\n---",
            "資料來源：2026 司法特考專屬資料庫"
        ]
        return "\n".join(result)
    except Exception as e:
        return f"資料庫讀取異常：{str(e)}"

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
    if "刑法" in event.message.text:
        reply_text = get_random_law()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
