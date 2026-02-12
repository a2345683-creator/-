import os
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)

# --- 設定金鑰 ---
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 爬蟲核心功能：防呆加強版 ---
def get_random_criminal_law():
    try:
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('div', class_='law-article')
            
            if not articles:
                return "抓取失敗：找不到法條。"
            
            # --- 修正重點開始：嘗試最多 10 次 ---
            for _ in range(10):
                random_article = random.choice(articles)
                
                # 先檢查這些格子存不存在 (防呆)
                law_no_div = random_article.find('div', class_='line-0000')
                law_content_div = random_article.find('div', class_='line-0002')
                
                # 只有當「條號」和「內容」都有抓到時，才回傳
                if law_no_div and law_content_div:
                    law_no = law_no_div.text.strip()
                    law_content = law_content_div.text.strip()
                    return f"【刑法隨機抽考】\n\n{law_no}\n{law_content}\n\n(資料來源：全國法規資料庫)"
            # --- 修正重點結束 ---
            
            return "運氣不好，連續抽到格式不符的法條，請再試一次！"
        else:
            return "連線失敗，法務部網站可能暫時無法存取。"
            
    except Exception as e:
        return f"發生錯誤：{str(e)}"

# --- LINE Webhook ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- 訊息處理 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    
    if "刑法" in msg:
        reply_text = get_random_criminal_law()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
