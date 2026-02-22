import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re
import time

st.title("🚌 りっちゃん＆パパのバス予報")

URL_A = "https://transfer-cloud.navitime.biz/tobubus/approachings?departure-busstop=00310731&arrival-busstop=00310765"
URL_B = "https://transfer-cloud.navitime.biz/tobubus/approachings?departure-busstop=00310731&arrival-busstop=00310737"

def get_bus_data(target_url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # サーバー上でChromeを動かすための設定なのだ！
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(target_url)
        time.sleep(3)
        body_text = driver.find_element("tag name", "body").text
        match = re.search(r"約\d+分", body_text)
        return match.group() if match else "時間外なのだ"
    except:
        return "エラーなのだ"
    finally:
        driver.quit()

if st.button('最新のバスを調べるのだ！'):
    with st.spinner('バスを探してるのだ...'):
        res_a = get_bus_data(URL_A)
        res_b = get_bus_data(URL_B)
        col1, col2 = st.columns(2)
        with col1: st.metric("上尾駅行き", res_a)
        with col2: st.metric("宮原駅行き", res_b)