import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import re
import time
import os
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor # 影分身の術！
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 設定：ルート情報のまとめ ---
ROUTES = {
    "駅へ行く (🏢)": [
        {"name": "ルートA (上尾駅行)", "url": "https://transfer-cloud.navitime.biz/tobubus/approachings?departure-busstop=00310731&arrival-busstop=00310765"},
        {"name": "ルートB (宮原駅行)", "url": "https://transfer-cloud.navitime.biz/tobubus/approachings?departure-busstop=00310731&arrival-busstop=00310737"}
    ],
    "家へ帰る (🏠)": [
        {"name": "ルートC (上尾駅から)", "url": "https://transfer-cloud.navitime.biz/tobubus/approachings?departure-busstop=00310765&arrival-busstop=00310731"},
        {"name": "ルートD (宮原駅から)", "url": "https://transfer-cloud.navitime.biz/tobubus/approachings?departure-busstop=00310737&arrival-busstop=00310731"}
    ]
}

# 💾 【先発のみ】遅延データをCSVに保存する関数なのだ
def save_delay_to_sheets(route_name, delay_val):
    try:
        # 認証の設定なのだ
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # スプレッドシートを開く（名前を合わせておくのだ）
        sheet = client.open("bus_delay_log").sheet1
        
        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        is_weekend = "週末" if now_dt.weekday() >= 5 else "平日"
        
        # 行を追加するのだ！
        sheet.append_row([now_str, route_name, delay_val, is_weekend])
        st.success("スプレッドシートに記録したのだ！")
    except Exception as e:
        st.error(f"スプレッドシート保存エラーなのだ: {e}")

def get_bus_data(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    if os.path.exists('/usr/bin/chromedriver'):
        service = Service('/usr/bin/chromedriver')
    else:
        service = Service()

    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url)
        time.sleep(3)
        body_text = driver.find_element("tag name", "body").text
        
        # 1. 到着までの分数（複数取得）
        wait_times = re.findall(r"あと約\s*(\d+)\s*分", body_text)
        
        # 2. 先発の遅延情報（1つだけ取得）
        delay_match = re.search(r"(?:約\s*)?(\d+)\s*分遅れ|遅れなし", body_text)
        
        delay_val = "0"
        if delay_match:
            delay_val = delay_match.group(1) if delay_match.group(1) else "0"
        else:
            delay_val = None

        return wait_times, delay_val
        
    except Exception:
        return [], None
    finally:
        driver.quit()

# --- 画面表示 ---
st.set_page_config(page_title="いたまるバス予報 Pro", layout="centered", page_icon="🚌")
st.title("🚌 いたまるバス予報 Pro")
st.caption("〜爆速スキャン ＆ 複数表示モードなのだ〜")

tab1, tab2 = st.tabs(["🏢 駅へ行く", "🏠 家へ帰る"])

def show_ui(route_list, key_suffix):
    if st.button(f"全ルート同時スキャン！", key=f"btn_{key_suffix}"):
        # 🏎️ 並列処理で全ルートを一気に取得するのだ！
        with st.spinner("分身たちが調査中なのだ..."):
            with ThreadPoolExecutor(max_workers=len(route_list)) as executor:
                urls = [route['url'] for route in route_list]
                results = list(executor.map(get_bus_data, urls))

        for i, route in enumerate(route_list):
            wait_times, delay_val = results[i]
            
            with st.expander(f"📍 {route['name']}", expanded=True):
                if not wait_times and delay_val is None:
                    st.warning("運行情報が見当たらないのだ。")
                else:
                    # 【先発】の表示
                    first_val = f"約 {wait_times[0]} 分" if wait_times else "まもなく"
                    st.metric(label="【先発】", value=first_val, 
                              delta=f"{delay_val} 分遅れ" if delay_val != "0" else "遅れなし", 
                              delta_color="inverse")
                    
                    # 【次発以降】の表示
                    if len(wait_times) > 1:
                        sub_info = f"🥈 **次発**: 約 {wait_times[1]} 分"
                        if len(wait_times) > 2:
                            sub_info += f"　🥉 **次々発**: 約 {wait_times[2]} 分"
                        st.write(sub_info)
                    
                    # 【CSV保存】は先発の遅延のみ！
                    if delay_val is not None:
                        save_delay_to_sheets(route['name'], delay_val)

with tab1:
    show_ui(ROUTES["駅へ行く (🏢)"], "to_station")

with tab2:
    show_ui(ROUTES["家へ帰る (🏠)"], "to_home")

# 📊 履歴表示
if os.path.exists("bus_delay_log.csv"):
    st.divider()
    st.subheader("📊 直近の遅延履歴")
    df = pd.read_csv("bus_delay_log.csv")
    st.dataframe(df.tail(5))