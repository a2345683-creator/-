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

def get_random_law_from_web():
    try:
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return "連線失敗，請檢查網路。"

        soup = BeautifulSoup(response.text, 'html.parser')
        # 抓取所有法條區塊
        blocks = soup.find_all('div', class_='law-article')
        
        valid_laws = []
        for b in blocks:
            # --- 暴力解碼：抓取區塊內所有的 div 子層 ---
            divs = b.find_all('div', recursive=False)
            
            # 只要有兩個以上的格子，就一定有條號跟內容
            if len(divs) >= 2:
                # 第一個格子就是條號 (例如：第 38-3 條)
                no_text = divs[0].get_text(strip=True)
                
                # 後面所有的格子通通接起來當內容，並強制換行
                content_list = [d.get_text(strip=True) for d in divs[1:] if d.get_text(strip=True)]
                full_content = "\n".join(content_list)
                
                # 只要條號有「第」這個字，就存進清單
                if "第" in no_text and len(full_content) > 5:
                    valid_laws.append({"no": no_text, "content": full_content})

        if not valid_laws:
            # 如果還是失敗，嘗試抓取表格 row 模式
            rows = soup.find_all('div', class_='row')
            for r in rows:
                cols = r.find_all('div', recursive=False)
                if len(cols) >= 2:
                    no_t = cols[0].get_text(strip=True)
                    data_t = "\n".join([c.get_text(strip=True) for c in cols[1:]])
                    if "第" in no_t:
                        valid_laws.append({"no": no_t, "content": data_t})

        if not valid_laws:
            return "搜尋完成，但網頁結構異常，請稍後再試。"

        target = random.choice(valid_laws)
        
        return f"📖 【刑法隨機抽考】\n\n📌 {target['no']}\n\n{target['content']}\n\n---\n資料來源：全國法規資料庫"
            
    except Exception as e:
        return f"程式錯誤：{str(e)}"

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
        reply_text = get_random_law_from_web()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
