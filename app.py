import os
import random
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 功能 1：工時計算邏輯 (處理 LIFF 送回的字串) ---
def handle_work_calc(text):
    try:
        # 格式：工時,班別,時間1,時間2,時間3
        data = text.split(',')
        shift = "日班 ☀️" if data[1] == 'D' else "夜班 🌙"
        fmt = "%H:%M"
        t1, t2, t3 = datetime.strptime(data[2], fmt), datetime.strptime(data[3], fmt), datetime.strptime(data[4], fmt)
        
        # 簡易公式：總時數 = (t3 - t1) / 3600 秒
        total_seconds = (t3 - t1).seconds
        total_hours = total_seconds / 3600
        
        return f"📊 【工時試算報告】\n\n班別：{shift}\n上下班：{data[2]} ~ {data[4]}\n\n✅ 當日總時數：{total_hours:.2f} 小時"
    except Exception as e:
        return "工時計算異常，請確認時間格式。"

# --- 功能 2：刑法抽考邏輯 (LawSingle 精準版) ---
def get_random_criminal_law():
    try:
        base_url = "https://law.moj.gov.tw"
        all_law_url = f"{base_url}/LawClass/LawAll.aspx?pcode=C0000001"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(all_law_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'LawSingle\.aspx\?pcode=C0000001'))
        target = random.choice(links)
        law_no = target.get_text(strip=True)
        target_url = f"{base_url}/LawClass/{target['href'].replace('../', '')}"
        
        single_res = requests.get(target_url, headers=headers)
        single_soup = BeautifulSoup(single_res.text, 'html.parser')
        content_tags = single_soup.select('.col-data, .line-0002')
        lines = [t.get_text(strip=True) for t in content_tags if t.get_text(strip=True) != law_no]
        
        return f"📖 【刑法抽考】\n\n📌 {law_no}\n\n" + "\n".join(lines)
    except:
        return "連線繁忙，請再抽一次！"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    # 判斷訊息開頭
    if msg.startswith("工時"):
        reply = handle_work_calc(msg)
    elif "刑法" in msg:
        reply = get_random_criminal_law()
    else:
        return # 不處理其他閒聊

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
