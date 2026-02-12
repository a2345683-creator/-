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

# --- 終極優化版：先篩選後隨機 ---
def get_random_criminal_law():
    try:
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return "連線失敗，法務部網站暫時無法存取。"

        soup = BeautifulSoup(response.text, 'html.parser')
        # 抓取所有法條區塊
        all_blocks = soup.find_all('div', class_='law-article')
        
        # 建立「黃金名單」：只存放真正有效的法條
        valid_laws = []
        
        for block in all_blocks:
            law_no_div = block.find('div', class_='line-0000') # 條號
            law_content_div = block.find('div', class_='line-0002') # 內容
            
            # 只有當「條號」和「內容」都存在，且內容不是空的時候才加入
            if law_no_div and law_content_div:
                no_text = law_no_div.text.strip()
                content_text = law_content_div.text.strip()
                
                # 排除掉章節標題（通常很短）或空法條
                if no_text and content_text and "第" in no_text:
                    valid_laws.append({
                        "no": no_text,
                        "content": content_text
                    })
        
        if not valid_laws:
            return "搜尋完畢，但沒找到有效的法條內容。"

        # 從黃金名單隨機抽一條
        target = random.choice(valid_laws)
        
        return f"【刑法隨機抽考】\n\n{target['no']}\n{target['content']}\n\n(資料來源：全國法規資料庫)"
            
    except Exception as e:
        return f"程式執行發生錯誤：{str(e)}"

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
        # 直接呼叫優化後的函式
        reply_text = get_random_criminal_law()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
