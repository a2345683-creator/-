import os
import random
import requests
import re
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

def get_random_law_hyper_robust():
    try:
        base_url = "https://law.moj.gov.tw"
        # 刑法全文頁面
        all_law_url = f"{base_url}/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
        
        # 1. 抓取全文頁面，獲取所有 LawSingle 連結
        response = requests.get(all_law_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- 核心修正：直接掃描所有包含 LawSingle 且屬於刑法代碼的連結 ---
        # 這樣就算滑鼠沒移上去，程式也能直接從代碼層級把連結挖出來
        law_links = soup.find_all('a', href=re.compile(r'LawSingle\.aspx\?pcode=C0000001'))
        
        if not law_links:
            # 備援方案：如果 a 標籤抓不到，嘗試從 class 抓取
            law_links = soup.select('div.line-0000 a')

        if not law_links:
            return "偵測不到條號連結，可能是政府網站暫時阻擋，請稍後再試一次！"

        # 隨機挑一個連結
        target = random.choice(law_links)
        target_url = base_url + "/LawClass/" + target['href'].replace("../", "")
        law_no = target.get_text(strip=True) or "隨機條文"
        
        # 2. 進入單一法條頁面抓取正式內容
        single_res = requests.get(target_url, headers=headers, timeout=15)
        single_soup = BeautifulSoup(single_res.text, 'html.parser')
        
        # 抓取單一頁面的內容 (line-0002)
        content_tags = single_soup.select('div.line-0002')
        
        lines = []
        for ct in content_tags:
            t = ct.get_text(strip=True)
            if t:
                # 處理項次排版
                if t.isdigit():
                    lines.append(f"\n({t})")
                else:
                    lines.append(t)
        
        full_content = " ".join(lines).replace("\n ", "\n").strip()
        
        return f"📖 【刑法抽抽抽】\n\n📌 {law_no}\n\n{full_content}\n\n---\n資料來源：全國法規資料庫)"
            
    except Exception as e:
        return f"連線不穩定，請再按一次圖片按鈕！\n(錯誤訊息: {str(e)[:20]})"

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
        reply_text = get_random_law_hyper_robust()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
