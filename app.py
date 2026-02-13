import os
import random
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
from flask import Flask, request, abort, render_template_string
from linebot import LineBotApi, WebhookHandler 
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
app = Flask(__name__)

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

# --- 1. 工時計算邏輯 (名稱更換為總工時) ---
def handle_work_calc(msg_text, user_name):
    try:
        data = [i.strip() for i in msg_text.split(',')]
        if len(data) < 8: return "❌ 資料欄位不足。"
        
        shift_icon = "日班 ☀️" if data[1] == 'D' else "夜班 🌙"

        def get_diff_hours(start_str, end_str):
            fmt = "%H:%M"
            s, e = datetime.strptime(start_str, fmt), datetime.strptime(end_str, fmt)
            diff = (e - s).total_seconds() / 3600
            return diff + 24 if diff < 0 else diff

        total_span = get_diff_hours(data[2], data[3])
        break1 = get_diff_hours(data[4], data[5])
        break2 = get_diff_hours(data[6], data[7])
        net_hours = total_span - break1 - break2

        return (f"📊 【工時試算報告】\n"
                f"👤 員工：{user_name}\n"
                f"📅 班別：{shift_icon}\n"
                f"----------------\n"
                f"🍽️ 總休息：{(break1 + break2):.2f} 小時\n"
                f"✅ 總工時：{net_hours:.2f} 小時")
    except Exception as e:
        return f"⚠️ 計算失敗：{str(e)}"

# --- 2. 刑法抽抽抽 ---
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
        return "連線繁忙"
# --- 3. 台南掛號導航 Flex Message (修正 404 連結) ---
def get_hospital_flex():
    return {
      "type": "bubble",
      "header": { "type": "box", "layout": "vertical", "contents": [{ "type": "text", "text": "🏥 台南醫療導航", "weight": "bold", "size": "xl", "color": "#FFFFFF" }], "backgroundColor": "#0088EE" },
      "body": {
        "type": "box", "layout": "vertical", "contents": [
          { "type": "button", "action": { "type": "uri", "label": "永康奇美醫院", "uri": "https://vcloud.chimei.org.tw/OprApp/Registration/RegMenu" }, "style": "primary", "color": "#E67E22", "margin": "md" },
          { "type": "button", "action": { "type": "uri", "label": "成大醫院", "uri": "https://service.hosp.ncku.edu.tw/Tandem/RegSelectorNet.aspx" }, "style": "primary", "color": "#3498DB", "margin": "md" },
          # 修正安南醫院連結，直接連至掛號入口
          { "type": "button", "action": { "type": "uri", "label": "安南醫院", "uri": "https://www.tmanh.org.tw/RegSelectorNet.aspx" }, "style": "primary", "color": "#9B59B6", "margin": "md" },
          # 修正市立醫院與部南醫院連結
          { "type": "button", "action": { "type": "uri", "label": "台南市立醫院", "uri": "https://www.tmh.org.tw/RegSelectorNet.aspx" }, "style": "primary", "color": "#2ECC71", "margin": "md" }
        ]
      },
      "footer": {
        "type": "box", "layout": "vertical", "contents": [
          { "type": "text", "text": "⚠️ 若無法開啟請嘗試重新整理", "size": "xs", "color": "#AAAAAA", "align": "center" }
        ]
      }
    }
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    # ... (獲取名稱的邏輯保留) ...

    if msg.startswith("工時"):
        reply = handle_work_calc(msg, user_name)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    elif "刑法" in msg:
        reply = get_random_criminal_law()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    elif "掛號" in msg: # <--- 新增這一塊
        flex_contents = get_hospital_flex()
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="台南掛號導航", contents=flex_contents))
    else: return
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
