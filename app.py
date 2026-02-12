import os
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

def get_random_law_from_web():
    try:
        url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return "連線失敗，請稍後再試。"

        soup = BeautifulSoup(response.text, 'html.parser')
        # 抓取所有法條主區塊
        blocks = soup.select('div.law-article')
        
        valid_laws = []
        for b in blocks:
            # --- 核心修正：精準抓取條號與內容標籤 ---
            # line-0000 是條號，line-0002 是法條內文
            no_tag = b.select_one('.line-0000')
            content_tags = b.select('.line-0002')
            
            if no_tag and content_tags:
                no_text = no_tag.get_text(strip=True)
                
                # 處理每一項內容，確保 1, 2, 3 會換行
                content_lines = []
                for ct in content_tags:
                    text = ct.get_text(strip=True)
                    if text:
                        # 如果是純數字項次，稍微美化它
                        if text.isdigit():
                            content_lines.append(f"\n({text})")
                        else:
                            content_lines.append(text)
                
                full_content = "\n".join(content_lines).replace("\n\n", "\n").strip()
                
                if "第" in no_text and len(full_content) > 5:
                    valid_laws.append({"no": no_text, "content": full_content})

        if not valid_laws:
            return "掃描完成，但網頁標籤定位失效，請檢查資料庫連結。"

        target = random.choice(valid_laws)
        
        # 按照你要求的「明確指出第幾條」排版
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
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
