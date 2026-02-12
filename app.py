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
            return "連線失敗，請稍後再試。"

        soup = BeautifulSoup(response.text, 'html.parser')
        blocks = soup.find_all('div', class_='law-article')
        
        valid_laws = []
        for b in blocks:
            divs = b.find_all('div', recursive=False)
            if len(divs) >= 2:
                # 1. 抓取條號 (如：第 79-1 條)
                no_text = divs[0].get_text(strip=True)
                
                # 2. 抓取內容並排版
                content_parts = []
                for d in divs[1:]:
                    text = d.get_text(strip=True)
                    if text:
                        # 如果是純數字（項次），排版時稍微縮排
                        if text.isdigit():
                            content_parts.append(f"\n({text})")
                        else:
                            content_parts.append(text)
                
                # 將內容組合成一段一段的文字
                full_content = " ".join(content_parts).replace("\n ", "\n").strip()
                
                if "第" in no_text and len(full_content) > 5:
                    valid_laws.append({"no": no_text, "content": full_content})

        if not valid_laws:
            return "目前無法解析法條，請再試一次。"

        target = random.choice(valid_laws)
        
        # --- 最終視覺排版：明確區分條號與內容 ---
        result = [
            "📖 【刑法抽抽抽】",
            f"\n📌 {target['no']}",  # 明確指出第幾條
            "\n" + target['content'], # 後面裁示內容
            "\n---",
            "資料來源：全國法規資料庫"
        ]
        
        return "\n".join(result)
            
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
