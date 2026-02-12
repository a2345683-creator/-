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

# --- 設定金鑰 (從環境變數讀取) ---
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 爬蟲核心功能：抓取刑法 ---
def get_random_criminal_law():
    try:
        # pcode=C0000001 是「中華民國刑法」的專屬代碼
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 找到網頁上所有的法條區塊
            articles = soup.find_all('div', class_='law-article')
            
            if not articles:
                return "抓取失敗：找不到法條，可能是法務部網站改版了。"
            
            # 隨機挑選一條
            random_article = random.choice(articles)
            
            # 抓取條號與內容
            law_no = random_article.find('div', class_='line-0000').text.strip()
            law_content = random_article.find('div', class_='line-0002').text.strip()
            
            # 組合回傳文字
            result = f"【刑法隨機抽考】\n\n{law_no}\n{law_content}\n\n(資料來源：全國法規資料庫)"
            return result
        else:
            return "連線失敗，法務部網站可能暫時無法存取。"
            
    except Exception as e:
        return f"發生錯誤：{str(e)}"

# --- LINE Webhook 監聽接口 ---
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
    
    # 當使用者輸入包含「刑法」關鍵字時，才去抓法條
    if "刑法" in msg:
        reply_text = get_random_criminal_law()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
