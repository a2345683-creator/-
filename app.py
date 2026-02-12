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

# 設定金鑰 (從 Render 的環境變數讀取)
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 核心爬蟲功能：自動前往全國法規資料庫抓取 ---
def get_random_law_from_web():
    try:
        # 刑法全文網址
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return "連線失敗，請檢查政府網站是否正常。"

        soup = BeautifulSoup(response.text, 'html.parser')
        # 抓取所有法條區塊
        blocks = soup.find_all('div', class_='law-article')
        
        valid_laws = []
        for b in blocks:
            # 精準鎖定：line-0000 是條號，line-0002 是內容
            no_div = b.find('div', class_='line-0000')
            content_divs = b.find_all('div', class_='line-0002')
            
            if no_div and content_divs:
                no_text = no_div.get_text(strip=True)
                
                # 保留換行結構，將每一項分開
                content_list = []
                for d in content_divs:
                    t = d.get_text(strip=True)
                    if t:
                        content_list.append(t)
                
                full_content = "\n".join(content_list)
                
                # 過濾掉章節標題
                if "第" in no_text and len(full_content) > 2:
                    valid_laws.append({"no": no_text, "content": full_content})

        if not valid_laws:
            return "掃描完成，但格式解析不完全，請再試一次。"

        # 隨機抽一條
        target = random.choice(valid_laws)
        
        # 按照你要求的格式呈現：明確指出第幾條，後面裁示內容
        result = [
            "📖 【刑法抽抽抽】",
            f"\n📌 {target['no']}",
            f"\n{target['content']}",
            "\n---",
            "資料來源：全國法規資料庫"
        ]
        return "\n".join(result)
            
    except Exception as e:
        return f"執行錯誤：{str(e)}"

# --- LINE Webhook 接口 ---
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
        reply_text = get_random_law_from_web()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
