import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import re
import time
import os
import json
import pandas as pd
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import jpholiday

# --- 1. 時間の設定（日本時間 JST） ---
JST = timezone(timedelta(hours=+9), 'JST')

# --- 2. ルート設定 ---
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

# --- 3. スプレッドシート保存・読み込み用の認証関数 ---
# --- 修正版：ここを書き換えるのだ ---
def get_gspread_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 1. まずは Web版(Secrets) があるかチェック
    try:
        if "gcp_service_account" in st.secrets:
            service_account_info = json.loads(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
            return gspread.authorize(creds)
    except:
        # Secretsがない（またはエラー）ならスルーして下に行くのだ
        pass

    # 2. Web版がダメなら、ローカルの credentials.json を探すのだ
    if os.path.exists('credentials.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        return gspread.authorize(creds)
    else:
        # どっちもなかったらエラーを出すのだ
        raise FileNotFoundError("認証情報（Secrets または credentials.json）が見つからないのだ！")

def save_delay_to_sheets(route_name, delay_val):
    try:
        client = get_gspread_client()
        sheet = client.open("bus_delay_log").sheet1
        
        now_dt = datetime.now(JST)
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # 🗓️ 祝日・週末判定のパワーアップ！
        is_holiday = jpholiday.is_holiday(now_dt.date())
        if is_holiday:
            day_type = f"祝日({jpholiday.is_holiday_name(now_dt.date())})"
        elif now_dt.weekday() >= 5:
            day_type = "週末"
        else:
            day_type = "平日"
        
        # スプレッドシートに書き込む（day_typeを保存！）
        sheet.append_row([now_str, route_name, delay_val, day_type])
    except Exception as e:
        st.error(f"保存エラーなのだ: {e}")

# --- 4. スクレイピング関数 ---
def get_bus_data(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # 環境に応じたChromeDriverの設定
    if os.path.exists('/usr/bin/chromedriver'):
        service = Service('/usr/bin/chromedriver')
    else:
        service = Service()

    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url)
        time.sleep(3)
        body_text = driver.find_element("tag name", "body").text
        
        wait_times = re.findall(r"あと約\s*(\d+)\s*分", body_text)
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

# --- 5. UI（Streamlit画面） ---
st.set_page_config(page_title="いたまるバス予報 Pro", layout="centered", page_icon="🚌")
st.title("🚌 いたまるバス予報 Pro")
st.caption(f"現在の日本時間: {datetime.now(JST).strftime('%H:%M:%S')}")

tab1, tab2 = st.tabs(["🏢 駅へ行く", "🏠 家へ帰る"])

def show_ui(route_list, key_suffix):
    if st.button(f"最新のバスをスキャン！", key=f"btn_{key_suffix}"):
        with st.spinner("並列スキャン中なのだ..."):
            with ThreadPoolExecutor(max_workers=len(route_list)) as executor:
                urls = [route['url'] for route in route_list]
                results = list(executor.map(get_bus_data, urls))

        for i, route in enumerate(route_list):
            wait_times, delay_val = results[i]
            with st.expander(f"📍 {route['name']}", expanded=True):
                if not wait_times and delay_val is None:
                    st.warning("バスが走っていないか、取得失敗なのだ。")
                else:
                    first_val = f"約 {wait_times[0]} 分" if wait_times else "まもなく"
                    st.metric(label="【到着まで】", value=first_val, 
                              delta=f"{delay_val} 分遅れ" if delay_val != "0" else "遅れなし", 
                              delta_color="inverse")
                    
                    if len(wait_times) > 1:
                        st.write(f"🥈 **次発**: 約 {wait_times[1]} 分")
                    
                    if delay_val is not None:
                        save_delay_to_sheets(route['name'], delay_val)
                        st.success(f"スプレッドシートに記録完了！({delay_val}分遅れ)")

with tab1:
    show_ui(ROUTES["駅へ行く (🏢)"], "to_station")
with tab2:
    show_ui(ROUTES["家へ帰る (🏠)"], "to_home")

# --- 6. 履歴表示（スプレッドシートから読み込み） ---
st.divider()
if st.checkbox("📊 クラウドの履歴を表示する"):
    try:
        client = get_gspread_client()
        # スプレッドシート名が「bus_delay_log」であることを確認するのだ！
        sheet = client.open("bus_delay_log").sheet1
        data = sheet.get_all_records()
        
        if data:
            df_log = pd.DataFrame(data)
            st.subheader("🗓️ 直近の遅延ログ")
            st.dataframe(df_log.tail(10), use_container_width=True)
        else:
            st.info("データがまだ空っぽなのだ。スキャンしてみてほしいのだ！")
    except Exception as e:
        st.error(f"履歴の読み出しに失敗したのだ。設定を確認してほしいのだ: {e}")