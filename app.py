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

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

def get_random_criminal_law():
    try:
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return "連線失敗，政府網站可能在維修。"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 建立黃金名單
        valid_laws = []
        
        # 策略 A：尋找標準法規格式 (law-article)
        articles = soup.find_all('div', class_='law-article')
        
        # 如果策略 A 沒抓到，嘗試策略 B：尋找表格行格式 (row)
        if not articles:
            articles = soup.find_all('div', class_='row')

        for block in articles:
            # 嘗試抓取條號 (可能叫 line-0000 或 col-no)
            no_div = block.find('div', class_='line-0000') or block.find('div', class_='col-no')
            # 嘗試抓取內容 (可能叫 line-0002 或 col-data)
            content_div = block.find('div', class_='line-0002') or block.find('div', class_='col-data')
            
            if no_div and content_div:
                no_text = no_div.get_text(strip=True)
                content_text = content_div.get_text(strip=True)
                
                # 過濾掉廢止或空條文
                if "第" in no_text and len(content_text) > 5:
                    valid_laws.append({"no": no_text, "content": content_text})

        if not valid_laws:
            # 增加除錯資訊
            return f"掃描完成，發現 {len(articles)} 個區塊，但內容過濾後為 0。請再試一次！"

        target = random.choice(valid_laws)
        return f"【刑法隨機抽考】\n\n{target['no']}\n{target['content']}\n\n(資料來源：全國法規資料庫)"
            
    except Exception as e:
        return f"程式執行錯誤：{str(e)}"

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
