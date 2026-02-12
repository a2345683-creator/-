import os
import random
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
from flask import Flask, request, abort, render_template_string
# --- 【關鍵修正：補上這一行】 ---
from linebot import LineBotApi, WebhookHandler 
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 設定 LINE 密鑰
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 1. 網頁讀取功能 (提供 LIFF 選單介面) ---
@app.route('/')
@app.route('/index.html')
def index():
    try:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, 'index.html')
        with open(file_path, 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except Exception as e:
        return f"網頁讀取失敗：{str(e)}"

# --- 2. 工時計算邏輯 (處理選單傳回的資料) ---
def handle_work_calc(msg_text):
    try:
        data = [i.strip() for i in msg_text.split(',')]
        if len(data) < 5: return "資料格式不完整。"
        shift_name = "日班 ☀️" if data[1] == 'D' else "夜班 🌙"
        
        def parse_time(t_str):
            for fmt in ("%H:%M", "%H:%M:%S"):
                try: return datetime.strptime(t_str, fmt)
                except: continue
            raise ValueError("時間格式錯誤")

        t1, t3 = parse_time(data[2]), parse_time(data[4])
        diff = (t3 - t1).total_seconds() / 3600
        if diff < 0: diff += 24 # 支援跨午夜計算
        
        return f"📊 【工時報告】\n👤 員工：楊秦宇\n📅 班別：{shift_name}\n⏰ 累計：{diff:.2f} 小時"
    except Exception as e:
        return f"⚠️ 計算出錯：{str(e)}"

# --- 3. 刑法抽考邏輯 (從全國法規資料庫抓取) ---
def get_random_criminal_law():
    try:
        base_url = "https://law.moj.gov.tw"
        url = f"{base_url}/LawClass/LawAll.aspx?pcode=C0000001"
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'LawSingle\.aspx\?pcode=C0000001'))
        target = random.choice(links)
        law_no = target.get_text(strip=True)
        t_url = f"{base_url}/LawClass/{target['href'].replace('../', '')}"
        
        s_res = requests.get(t_url)
        s_soup = BeautifulSoup(s_res.text, 'html.parser')
        content = s_soup.select('.col-data, .line-0002')
        lines = [t.get_text(strip=True) for t in content if t.get_text(strip=True) != law_no]
        return f"📖 【刑法抽抽抽】\n📌 {law_no}\n\n" + "\n".join(lines)
    except:
        return "連線忙碌中，請稍後再試。"

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
    if msg.startswith("工時"):
        reply = handle_work_calc(msg)
    elif "刑法" in msg:
        reply = get_random_criminal_law()
    else: return
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
