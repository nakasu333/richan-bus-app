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

def get_bus_times(url):
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
        time.sleep(5) # 読み込みをしっかり待つ
        
        # 1. ページ全体のテキストをバサッと取得
        body_text = driver.find_element("tag name", "body").text
        
        # 🎯 魔法の正規表現なのだ！
        # 「あと約」から始まって、数字があって、「分」で終わるものだけを全部拾う
        # これで「○分遅れ」や「○個前」というノイズは完全に無視できるのだ🤤
        real_times = re.findall(r"あと約\s*(\d+)\s*分", body_text)
        
        # もし「あと約〜」で見つからなかった場合の予備（「まもなく」判定など）
        if not real_times:
            if "まもなく" in body_text:
                return ["まもなく"]
            return ["情報なし"]
            
        return real_times # 見つかった数字のリスト [ "8", "25" ] が返る
        
    except Exception:
        return ["エラー"]
    finally:
        driver.quit()

# --- 画面表示 ---
st.set_page_config(page_title="いたまるバス予報 Pro", layout="centered", page_icon="🚌")
st.title("🚌 いたまるバス予報 Pro")
st.caption("〜ノイズ除去・次発対応版なのだ〜")

tab1, tab2 = st.tabs(["🏢 駅へ行く", "🏠 家へ帰る"])

def show_route_ui(route_list, key_suffix):
    if st.button(f"最新のバスをスキャンするのだ！", key=f"btn_{key_suffix}"):
        for route in route_list:
            # 展開パネルでルートごとに見やすくするのだ
            with st.expander(f"📍 {route['name']}", expanded=True):
                with st.spinner(f"解析中..."):
                    bus_list = get_bus_times(route['url'])
                    
                    if bus_list[0] in ["情報なし", "エラー"]:
                        st.warning("現在、運行情報が見当たらないのだ。")
                    else:
                        # 先発を表示
                        first = bus_list[0]
                        val = "まもなく発車！" if first == "まもなく" else f"約 {first} 分"
                        st.metric(label="【先発】", value=val)
                        
                        # 次発・次々発があれば表示
                        if len(bus_list) > 1:
                            sub_info = ""
                            if len(bus_list) > 1:
                                sub_info += f"🥈 **次発**: 約 {bus_list[1]} 分　"
                            if len(bus_list) > 2:
                                sub_info += f"🥉 **次々発**: 約 {bus_list[2]} 分"
                            st.write(sub_info)

with tab1:
    st.header("いってらっしゃいなのだ！")
    show_route_ui(ROUTES["駅へ行く (🏢)"], "to_station")

with tab2:
    st.header("お疲れさまなのだ！")
    show_route_ui(ROUTES["家へ帰る (🏠)"], "to_home")