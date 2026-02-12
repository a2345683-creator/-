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
        # 抓取所有法條區塊
        blocks = soup.find_all('div', class_='law-article')
        
        law_database = [] # 這就是我們的「即時對照表」

        for b in blocks:
            # 1. 嘗試用標籤名抓取
            no_tag = b.find('div', class_='line-0000')
            content_tags = b.find_all('div', class_='line-0002')
            
            # 2. 【反查機制】如果標籤抓不到，改用「位置」抓取 (抓區塊內第一個 div)
            if not no_tag:
                all_divs = b.find_all('div', recursive=False)
                if len(all_divs) >= 2:
                    no_text = all_divs[0].get_text(strip=True)
                    content_list = [d.get_text(strip=True) for d in all_divs[1:]]
                else:
                    continue
            else:
                no_text = no_tag.get_text(strip=True)
                content_list = [d.get_text(strip=True) for d in content_tags]

            # 整理內容排版 (處理項次 1, 2, 3)
            formatted_content = []
            for t in content_list:
                if t:
                    # 如果內容是單純數字，代表是項次，幫它換行
                    if t.isdigit():
                        formatted_content.append(f"\n({t})")
                    else:
                        formatted_content.append(t)
            
            full_text = " ".join(formatted_content).replace("\n ", "\n").strip()
            
            # 只要有條號且內容夠長，就存入對照表
            if "第" in no_text and len(full_text) > 5:
                law_database.append({"no": no_text, "content": full_text})

        if not law_database:
            return "資料解析失敗，請檢查網路連線。"

        # 從對照表隨機抽題
        target = random.choice(law_database)
        
        return f"📖 【刑法抽抽抽】\n\n📌 {target['no']}\n\n{target['content']}\n\n---\n資料來源：全國法規資料庫 (已啟動反查機制)"
            
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
    if "刑法" in event.message.text:
        reply_text = get_random_law_from_web()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
