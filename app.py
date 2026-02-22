import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import re
import time
import os

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

def get_bus_time(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # 🌟 サーバーかPCかを判断してサービスを準備
    if os.path.exists('/usr/bin/chromedriver'):
        service = Service('/usr/bin/chromedriver')
    else:
        service = Service()

    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url) # 🌟 ここを url に修正したのだ！
        time.sleep(3)
        
        # 🎯 狙い撃ち作戦：大きな数字の「枠」だけを見る
        try:
            # 「approach-info-time」というクラス名の場所をピンポイントで探す
            target_element = driver.find_element("class name", "approach-info-time")
            info_text = target_element.text
            
            # 「まもなく」があれば優先
            if "まもなく" in info_text:
                return "まもなく"
            
            # 「約○分」を探す（数字だけ抜き取る）
            match = re.search(r"(\d+)", info_text)
            if match:
                return match.group(1)
        except:
            # 枠が見つからない時のバックアップ
            body_text = driver.find_element("tag name", "body").text
            match = re.search(r"約(\d+)分", body_text)
            if match:
                return match.group(1)

        return "不明"
    except Exception as e:
        return "エラー"
    finally:
        driver.quit()

# --- 画面表示 ---
st.set_page_config(page_title="いたまるバス予報", layout="centered")
st.title("🚌 いたまる専用バス予報")

tab1, tab2 = st.tabs(["🏢 駅へ行く", "🏠 家へ帰る"])

def show_route_ui(route_list, key_suffix):
    if st.button(f"最新のバスを調べるのだ！", key=f"btn_{key_suffix}"):
        cols = st.columns(len(route_list))
        for i, route in enumerate(route_list):
            with cols[i]:
                with st.spinner(f"{route['name']}を確認中..."):
                    wait_time = get_bus_time(route['url'])
                    
                    # 🌟 表示をきれいに整えるのだ
                    if wait_time == "まもなく":
                        display_val = "まもなく！"
                    elif wait_time == "不明" or wait_time == "エラー":
                        display_val = "情報なし"
                    else:
                        display_val = f"約 {wait_time} 分"
                        
                    st.metric(label=route['name'], value=display_val)

with tab1:
    st.header("いってらっしゃいなのだ！")
    show_route_ui(ROUTES["駅へ行く (🏢)"], "to_station")

with tab2:
    st.header("お疲れさまなのだ！")
    show_route_ui(ROUTES["家へ帰る (🏠)"], "to_home")