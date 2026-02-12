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
        # 模擬更真實的瀏覽器指紋，防止被政府網站阻擋
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        # 加入 timeout (5秒)，防止 Render 伺服器因等待過久而斷線
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8' # 強制設定編碼
        
        if response.status_code != 200:
            return f"政府網站回應異常 (代碼:{response.status_code})，請稍後再按一次。"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 嘗試抓取標準標籤 (law-article)
        articles = soup.find_all('div', class_='law-article')
        
        # 2. 如果標準標籤失效，嘗試抓取所有包含數字開頭的內容格 (備援方案)
        if not articles:
            articles = soup.find_all('div', class_='row')

        law_list = []
        for a in articles:
            # 獲取區塊內所有文字，並進行清理
            all_text = a.get_text(separator="|", strip=True).split("|")
            
            if len(all_text) >= 2:
                # 第一個非空的內容通常是條號
                no = all_text[0]
                # 剩下的內容組合成條文，並處理 1, 2, 3 項次的換行
                content_parts = []
                for p in all_text[1:]:
                    if p.isdigit():
                        content_parts.append(f"\n({p})")
                    else:
                        content_parts.append(p)
                
                content = " ".join(content_parts).replace("\n ", "\n").strip()
                
                if "第" in no and len(content) > 10:
                    law_list.append({"no": no, "content": content})

        if not law_list:
            return "目前全國法規資料庫連線不穩，建議多點擊幾次圖片按鈕試試！"

        target = random.choice(law_list)
        return f"📖 【刑法抽抽抽】\n\n📌 {target['no']}\n\n{target['content']}\n\n---\n資料來源：全國法規資料庫 (強韌解析版)"
            
    except Exception as e:
        return f"系統連線繁忙，請再試一次！(Error: {str(e)[:20]})"

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
