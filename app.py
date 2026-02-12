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

def get_random_law_single_fix():
    try:
        base_url = "https://law.moj.gov.tw"
        all_law_url = f"{base_url}/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
        
        # 1. 在總表抓取所有條號連結 (這部分你已經成功了！)
        response = requests.get(all_law_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        law_links = soup.find_all('a', href=re.compile(r'LawSingle\.aspx\?pcode=C0000001'))
        
        target = random.choice(law_links)
        law_no = target.get_text(strip=True)
        target_path = target['href'].replace("../", "")
        target_url = f"{base_url}/LawClass/{target_path}"
        
        # 2. 進入單一頁面 (LawSingle) 抓取內容
        single_res = requests.get(target_url, headers=headers, timeout=15)
        single_soup = BeautifulSoup(single_res.text, 'html.parser')
        
        # --- 根據 image_5f41f5.png 的精準修正 ---
        # 單一頁面的內容標籤通常叫做 .col-data
        content_tags = single_soup.select('.col-data, .line-0002, .law-reg-content-row')
        
        lines = []
        for ct in content_tags:
            t = ct.get_text(strip=True)
            if t and t != law_no:
                # 處理項次換行
                if t.isdigit():
                    lines.append(f"\n({t})")
                else:
                    lines.append(t)
        
        full_content = " ".join(lines).replace("\n ", "\n").strip()
        
        # 如果還是空，嘗試抓取所有在表格內的文字
        if not full_content:
            all_text_divs = single_soup.select('td, .LawContent')
            full_content = "\n".join([d.get_text(strip=True) for d in all_text_divs if len(d.get_text(strip=True)) > 10])

        return f"📖 【刑法抽抽抽】\n\n📌 {law_no}\n\n{full_content}\n\n---\n資料來源：全國法規資料庫"
            
    except Exception as e:
        return f"解析失敗，請再抽一次！\n(錯誤: {str(e)[:15]})"

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
        reply_text = get_random_law_single_fix()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
