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

def get_random_law_with_link():
    try:
        base_url = "https://law.moj.gov.tw"
        all_law_url = f"{base_url}/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        
        # 1. 抓取全文網頁，收集所有條號連結
        response = requests.get(all_law_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找所有條號的超連結 (a 標籤)
        # 這些連結通常在 class 為 line-0000 的 div 裡面
        law_links = soup.select('div.line-0000 a')
        
        if not law_links:
            return "目前抓不到條號連結，請確認政府網站是否改版。"

        # 隨機選一個法條連結
        target_link = random.choice(law_links)
        target_url = base_url + target_link['href']
        
        # 2. 點擊進入單一法條頁面 (LawSingle)
        single_response = requests.get(target_url, headers=headers, timeout=10)
        single_soup = BeautifulSoup(single_response.text, 'html.parser')
        
        # 抓取法條編號 (例如：第 38-3 條)
        law_no = target_link.get_text(strip=True)
        
        # 抓取法條內容 (單一頁面的內容通常在 .law-reg-content)
        content_divs = single_soup.select('div.line-0002')
        
        # 整理排版
        lines = []
        for d in content_divs:
            t = d.get_text(strip=True)
            if t:
                # 判斷是否為項次標號 (1, 2, 3...)
                if t.isdigit():
                    lines.append(f"\n({t})")
                else:
                    lines.append(t)
        
        full_content = " ".join(lines).replace("\n ", "\n").strip()
        
        return f"📖 【刑法抽抽抽】\n\n📌 {law_no}\n\n{full_content}\n\n---\n資料來源：全國法規資料庫"
            
    except Exception as e:
        return f"連線繁忙或格式解析失敗，請再試一次！\n(錯誤: {str(e)[:20]})"

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
        reply_text = get_random_law_with_link()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
