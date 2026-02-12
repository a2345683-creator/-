import os
import random
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
from flask import Flask, request, abort, render_template_string
from linebot import LineBotApi, WebhookHandler 
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 設定 LINE 密鑰
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

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

# --- 核心修正：接收 user_name 變數 ---
def handle_work_calc(msg_text, user_name):
    try:
        data = [i.strip() for i in msg_text.split(',')]
        if len(data) < 8: return "❌ 資料欄位不足，請重新填寫。"
        
        def get_diff(s_str, e_str):
            fmt = "%H:%M"
            s, e = datetime.strptime(s_str, fmt), datetime.strptime(e_str, fmt)
            diff = (e - s).total_seconds() / 3600
            return diff + 24 if diff < 0 else diff

        total_span = get_diff(data[2], data[3]) # 上班到下班
        b1_span = get_diff(data[4], data[5])    # 第一次休息
        b2_span = get_diff(data[6], data[7])    # 第二次休息
        net_hours = total_span - b1_span - b2_span

        # 這裡將固定名字換成了變數 user_name
        return (f"📊 【工時試算報告】\n"
                f"👤 員工：{user_name}\n"
                f"📅 班別：{'日班 ☀️' if data[1]=='D' else '夜班 🌙'}\n"
                f"----------------\n"
                f"⏱️ 總待命：{total_span:.2f} hr\n"
                f"🍽️ 總休息：{(b1_span + b2_span):.2f} hr\n"
                f"----------------\n"
                f"✅ 實作淨工時：{net_hours:.2f} 小時")
    except Exception as e:
        return f"⚠️ 計算失敗：{str(e)}"

# --- 刑法抽考邏輯 ---
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
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    
    # --- 關鍵修正：自動獲取使用者名稱 ---
    try:
        profile = line_bot_api.get_profile(event.source.user_id)
        user_name = profile.display_name
    except:
        user_name = "未知使用者"

    if msg.startswith("工時"):
        reply = handle_work_calc(msg, user_name) # 將名字傳進去
    elif "刑法" in msg:
        reply = get_random_criminal_law()
    else: return
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
