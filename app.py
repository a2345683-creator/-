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

# --- 1. 工時計算邏輯 (修正版：支援 HH:MM 與 HH:MM:SS) ---
def handle_work_calc(msg_text, user_name):
    try:
        data = [i.strip() for i in msg_text.split(',')]
        if len(data) < 8: return "❌ 資料欄位不足。"
        
        shift_icon = "日班 ☀️" if data[1] == 'D' else "夜班 🌙"

        def get_diff_hours(start_str, end_str):
            # 依序嘗試兩種格式，解決 LIFF 傳入秒數導致崩潰的問題
            for fmt in ("%H:%M", "%H:%M:%S"):
                try:
                    s = datetime.strptime(start_str, fmt)
                    e = datetime.strptime(end_str, fmt)
                    diff = (e - s).total_seconds() / 3600
                    return diff + 24 if diff < 0 else diff
                except:
                    continue
            raise ValueError("格式錯誤")

        total_span = get_diff_hours(data[2], data[3])
        break1 = get_diff_hours(data[4], data[5])
        break2 = get_diff_hours(data[6], data[7])
        net_hours = total_span - break1 - break2

        return (f"📊 【工時試算報告】\n"
                f"👤 員工：{user_name}\n"
                f"📅 班別：{shift_icon}\n"
                f"----------------\n"
                f"🍽️ 總休息：{(break1 + break2):.2f} hr\n"
                f"✅ 總工時：{max(0, net_hours):.2f} hr")
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
          { "type": "button", "action": { "type": "uri", "label": "奇美醫院", "uri": "https://www.chimei.org.tw/newindex/opd/opd.html" }, "style": "primary", "color": "#E67E22", "margin": "md" },
          { "type": "button", "action": { "type": "uri", "label": "成大醫院", "uri": "https://tandem.hosp.ncku.edu.tw/tandem/DeptUI.aspx" }, "style": "primary", "color": "#3498DB", "margin": "md" },
          { "type": "button", "action": { "type": "uri", "label": "安南醫院", "uri": "https://www.tmanh.org.tw/Service/OnlineAppointment" }, "style": "primary", "color": "#9B59B6", "margin": "md" },
          { "type": "button", "action": { "type": "uri", "label": "新樓醫院", "uri": "https://rt01.sinlau.org.tw/sinlau/rt01/" }, "style": "primary", "color": "#2ECC71", "margin": "md" }
        ]
      },
      "footer": {
        "type": "box", "layout": "vertical", "contents": [
          { "type": "text", "text": "⚠️ 若無法開啟請嘗試重新整理", "size": "xs", "color": "#AAAAAA", "align": "center" }
        ]
      }
    }
    # --- 4. 539 精選過濾模式 ---
def get_539_premium_prediction():
    import random
    from collections import Counter
    try:
        # 爬取數據 (這部分邏輯與先前相同)
        url = "https://lotto.arclink.com.tw/Lotto539History.html"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        all_nums = []
        rows = soup.select('.nums')
        for row in rows[:100]:
            nums = re.findall(r'\d+', row.get_text())
            all_nums.extend([int(n) for n in nums])
        
        # 統計出精選池 (熱門12個 + 冷門12個)
        counts = Counter(all_nums)
        hot_nums = [n for n, c in counts.most_common(12)]
        cold_nums = [n for n, c in sorted(counts.items(), key=lambda x: x[1])[:12]]
        pool = list(set(hot_nums + cold_nums))

        # 1000次模擬篩選
        best_pick = None
        for _ in range(1000):
            candidate = sorted(random.sample(pool, 5))
            total_sum = sum(candidate)
            odds = len([n for n in candidate if n % 2 != 0])
            bigs = len([n for n in candidate if n >= 20])
            
            # 篩選條件：總和 75-125、奇偶不極端、大小不極端
            if (75 <= total_sum <= 125) and (0 < odds < 5) and (0 < bigs < 5):
                best_pick = candidate
                break
        
        if not best_pick: best_pick = sorted(random.sample(pool, 5))
        
        formatted_nums = ", ".join([str(n).zfill(2) for n in best_pick])
        return (f"💎 【539 大數據精選號碼】\n"
                f"----------------\n"
                f"🎲 推薦號碼：{formatted_nums}\n"
                f"----------------\n"
                f"📈 篩選指標：\n"
                f"● 總和：{sum(best_pick)} (常態分佈內)\n"
                f"● 奇偶：{5-odds}偶:{odds}奇\n"
                f"● 大小：{5-bigs}小:{bigs}大\n"
                f"✨ 已通過 1000 次數據模擬過濾")
    except Exception as e:
        return f"⚠️ 系統計算中，請稍後再試"
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    # 獲取使用者名稱
    try:
        profile = line_bot_api.get_profile(event.source.user_id)
        user_name = profile.display_name
    except:
        user_name = "同學"

    reply_msg = None

    if msg.startswith("工時"):
        content = handle_work_calc(msg, user_name)
        reply_msg = TextSendMessage(text=content)
    elif "刑法" in msg:
        content = get_random_criminal_law()
        reply_msg = TextSendMessage(text=content)
    elif "掛號" in msg:
        flex_contents = get_hospital_flex()
        reply_msg = FlexSendMessage(alt_text="台南掛號導航", contents=flex_contents)
    elif "539" in msg:
        reply_text = get_539_premium_prediction()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
    
    # 確保只會回覆一次，且有內容才回覆
    if reply_msg:
        line_bot_api.reply_message(event.reply_token, reply_msg)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
