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

# --- 核心功能：抓取法條並超清爽排版 ---
def get_random_criminal_law():
    try:
        # 刑法網址
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return "連線失敗，請稍後再試。"

        soup = BeautifulSoup(response.text, 'html.parser')
        # 抓取所有法條大區塊
        blocks = soup.find_all('div', class_='law-article')
        
        valid_laws = []
        for b in blocks:
            # 找出區塊內所有的小格子 (div)
            divs = b.find_all('div', recursive=False)
            
            # 至少要有條號跟內容兩個格子才算有效
            if len(divs) >= 2:
                # --- 1. 抓取條號 ---
                # 通常第一個格子就是條號 (例如: 第 38-3 條)
                no_text = divs[0].get_text(strip=True)
                
                # --- 2. 抓取內容 (修正重點) ---
                # 我們不再去猜測內容是不是數字，而是把剩下所有的格子
                # 一個一個抓出來，並且用「換行符號」連接起來。
                content_lines = []
                for d in divs[1:]: # 從第二個格子開始抓
                    text = d.get_text(strip=True)
                    if text: # 只要有文字就保留
                        content_lines.append(text)
                
                # 用換行符號 (\n) 把所有內容接起來，確保 1, 2, 3 會獨自一行
                full_content = "\n".join(content_lines)
                
                # 過濾掉不是法條的東西 (例如章節標題)
                if "第" in no_text and len(full_content) > 2:
                    valid_laws.append({"no": no_text, "content": full_content})

        if not valid_laws:
            return "目前無法解析法條，請再試一次。"

        # 隨機抽一條
        target = random.choice(valid_laws)
        
        # --- 最終排版組合 ---
        result = [
            "📖 【刑法抽抽抽】",
            f"\n📌 {target['no']}",  # 條號獨立顯示在最上方，加個圖釘標示
            "\n" + target['content'], # 內容在下方，每一項都會自動換行
            "\n---",
            "(資料來源：全國法規資料庫)"
        ]
        
        return "\n".join(result)
            
    except Exception as e:
        return f"程式執行錯誤：{str(e)}"

# --- LINE Webhook 設定 (維持不變) ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- 訊息處理 (維持不變) ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if "刑法" in msg: # 只要訊息有「刑法」兩個字就觸發
        reply_text = get_random_criminal_law()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
