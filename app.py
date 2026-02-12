import os
import random
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
from flask import Flask, request, abort, render_template_string # 使用字串渲染最保險

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 【關鍵修正】解決 500 錯誤的讀取方式 ---
@app.route('/')
@app.route('/index.html')
def index():
    try:
        # 直接讀取同資料夾下的 index.html 內容
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return render_template_string(html_content)
    except Exception as e:
        return f"網頁讀取失敗：{str(e)}。請確認 index.html 是否在 GitHub 根目錄。"

# --- 工時計算邏輯 (跨午夜強韌版) ---
def handle_work_calc(msg_text):
    try:
        data = [i.strip() for i in msg_text.split(',')]
        if len(data) < 5: return "格式不完整"
        shift_name = "日班 ☀️" if data[1] == 'D' else "夜班 🌙"
        
        def parse_time(t_str):
            for fmt in ("%H:%M", "%H:%M:%S"):
                try: return datetime.strptime(t_str, fmt)
                except: continue
            raise ValueError("時間格式錯誤")

        t1, t3 = parse_time(data[2]), parse_time(data[4])
        diff = (t3 - t1).total_seconds() / 3600
        if diff < 0: diff += 24 
        
        return f"📊 【工時報告】\n👤 員工：楊秦宇\n📅 班別：{shift_name}\n⏰ 累計時數：{diff:.2f} 小時"
    except Exception as e:
        return f"⚠️ 計算出錯：{str(e)}"

# --- 刑法抽考邏輯 ---
def get_random_criminal_law():
    try:
        base_url = "https://law.moj.gov.tw"
        all_law_url = f"{base_url}/LawClass/LawAll.aspx?pcode=C0000001"
        res = requests.get(all_law_url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'LawSingle\.aspx\?pcode=C0000001'))
        target = random.choice(links)
        law_no = target.get_text(strip=True)
        target_url = f"{base_url}/LawClass/{target['href'].replace('../', '')}"
        
        s_res = requests.get(target_url)
        s_soup = BeautifulSoup(s_res.text, 'html.parser')
        content_tags = s_soup.select('.col-data, .line-0002')
        lines = [t.get_text(strip=True) for t in content_tags if t.get_text(strip=True) != law_no]
        return f"📖 【刑法抽抽抽】\n📌 {law_no}\n\n" + "\n".join(lines)
    except:
        return "連線繁忙，請再試一次！"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if msg.startswith("工時"):
        reply = handle_work_calc(msg)
    elif "刑法" in msg:
        reply = get_random_criminal_law()
    else:
        return 
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
