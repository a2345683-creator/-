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
        # 刑法全文網址
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return "連線失敗，請稍後再試。"

        soup = BeautifulSoup(response.text, 'html.parser')
        # 抓取所有潛在的法條區塊
        blocks = soup.find_all('div', class_='law-article')
        
        valid_laws = []
        for b in blocks:
            # 獲取該區塊內所有的子 div
            divs = b.find_all('div', recursive=False)
            
            # 通常第一個子 div 是條號，第二個之後是內容
            if len(divs) >= 2:
                no_text = divs[0].get_text(strip=True)
                # 合併後面所有內容 div 的文字
                content_text = "".join([d.get_text(strip=True) for d in divs[1:]])
                
                # 只要條號包含「第」且內容長度足夠，就視為有效法條
                if "第" in no_text and len(content_text) > 5:
                    valid_laws.append({"no": no_text, "content": content_text})

        if not valid_laws:
            # 如果還是失敗，嘗試更寬鬆的策略：抓取所有 row 格式
            rows = soup.find_all('div', class_='row')
            for r in rows:
                col_no = r.find('div', class_='col-no')
                col_data = r.find('div', class_='col-data')
                if col_no and col_data:
                    no_t = col_no.get_text(strip=True)
                    data_t = col_data.get_text(strip=True)
                    if "第" in no_t and len(data_t) > 5:
                        valid_laws.append({"no": no_t, "content": data_t})

        if not valid_laws:
            return f"掃描完成，抓到 {len(blocks)} 個原始區塊，但解析失敗。請檢查網頁是否改版。"

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
