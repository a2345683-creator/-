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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return "連連線失敗，請稍後再試。"

        soup = BeautifulSoup(response.text, 'html.parser')
        # 抓取所有法條大區塊
        blocks = soup.find_all('div', class_='law-article')
        
        valid_laws = []
        for b in blocks:
            # 抓取區塊內所有的 div
            divs = b.find_all('div')
            if not divs: continue
            
            # 第一個 div 通常是條號 (包含 38-3 這種格式)
            no_text = divs[0].get_text(strip=True)
            
            # 剩下的 div 是內容，我們要保留它們的獨立性
            content_items = []
            for d in divs[1:]:
                txt = d.get_text(strip=True)
                if txt and txt != no_text: # 避免重複抓到條號
                    # 如果內容是純數字（項次），幫它加個美化符號
                    if txt.isdigit():
                        content_items.append(f"\n【第 {txt} 項】")
                    else:
                        content_items.append(txt)
            
            # 組合成最終內容，確保每一項都換行
            full_content = "\n".join(content_items).replace("\n\n", "\n").strip()
            
            if "第" in no_text and len(full_content) > 5:
                valid_laws.append({"no": no_text, "content": full_content})

        if not valid_laws:
            return "掃描完成，但格式解析不完全，請再試一次。"

        target = random.choice(valid_laws)
        
        # --- 最終排版：確保條號與內容分明 ---
        result = [
            "📖 【刑法隨機抽考】",
            f"\n📌 {target['no']}",  # 這裡一定會出現「第 XXX 條」
            "\n" + target['content'],
            "\n---",
            "資料來源：全國法規資料庫"
        ]
        
        return "\n".join(result)
            
    except Exception as e:
        return f"發生錯誤：{str(e)}"

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
