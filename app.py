import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import io
import urllib.parse
import requests
import json
import time

# --- 1. 設定與翻譯 ---
translations = {
    "繁體中文 (TW)": {
        "title": "鴻海全球輿情監控系統",
        "sidebar_title": "設定面板",
        "gemini_label": "輸入 Google Gemini API Key",
        "days_label": "搜尋時間範圍 (天數)",
        "keywords_label": "輸入搜尋關鍵字 (用逗號隔開)",
        "keywords_hint": "例如: 鴻海, Fii, 電動車",
        "btn_start": "開始搜尋與分析",
        "download_btn": "下載 Excel 報表",
        "params": {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
        "prompt_lang": "Traditional Chinese"
    },
    "English (US)": {
        "title": "Foxconn Media Monitor",
        "sidebar_title": "Settings",
        "gemini_label": "Enter Gemini API Key",
        "days_label": "Search Range (Days)",
        "keywords_label": "Enter Keywords",
        "keywords_hint": "e.g., Foxconn, Fii, EV",
        "btn_start": "Start Search",
        "download_btn": "Download Excel",
        "params": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
        "prompt_lang": "English"
    },
    "Tiếng Việt (VN)": {
        "title": "Hệ thống Giám sát Foxconn",
        "sidebar_title": "Cài đặt",
        "gemini_label": "Nhập Gemini API Key",
        "days_label": "Phạm vi thời gian",
        "keywords_label": "Nhập từ khóa",
        "keywords_hint": "Ví dụ: Foxconn, Fii",
        "btn_start": "Bắt đầu tìm kiếm",
        "download_btn": "Tải xuống báo cáo",
        "params": {"hl": "vi", "gl": "VN", "ceid": "VN:vi"},
        "prompt_lang": "Vietnamese"
    },
    "Español (MX)": {
        "title": "Monitor Foxconn",
        "sidebar_title": "Configuración",
        "gemini_label": "Clave API Gemini",
        "days_label": "Rango de tiempo",
        "keywords_label": "Palabras clave",
        "keywords_hint": "Ej: Foxconn, Fii",
        "btn_start": "Iniciar búsqueda",
        "download_btn": "Descargar Excel",
        "params": {"hl": "es-419", "gl": "MX", "ceid": "MX:es-419"},
        "prompt_lang": "Spanish"
    },
    "Português (BR)": {
        "title": "Monitor Foxconn",
        "sidebar_title": "Configurações",
        "gemini_label": "Chave API Gemini",
        "days_label": "Intervalo de tempo",
        "keywords_label": "Palabras-chave",
        "keywords_hint": "Ex: Foxconn, Fii",
        "btn_start": "Iniciar pesquisa",
        "download_btn": "Baixar Excel",
        "params": {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
        "prompt_lang": "Portuguese"
    }
}

st.set_page_config(page_title="Foxconn Monitor", layout="wide")

# Sidebar
language_option = st.sidebar.selectbox("Language / 語言", list(translations.keys()))
t = translations[language_option]

st.title(f"🦊 {t['title']}")

st.sidebar.title(t['sidebar_title'])
gemini_key_input = st.sidebar.text_input(t['gemini_label'], type="password")
gemini_key = gemini_key_input.strip() if gemini_key_input else ""

days_selected = st.sidebar.slider(t['days_label'], 1, 7, 1)
time_param = f"when:{days_selected}d"

# 系統狀態顯示
st.sidebar.markdown("---")
st.sidebar.success("✅ System Ready (v3.1 Stable)")

# --- 2. 核心函數: 搜尋 ---
def search_google_rss(keyword, time_limit, params):
    base_url = "https://news.google.com/rss/search"
    query = f"{keyword} {time_limit}"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"{base_url}?q={encoded_query}&hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
    
    feed = feedparser.parse(rss_url)
    results = []
    for entry in feed.entries[:10]:
        pub_date = entry.published if 'published' in entry else datetime.now().strftime("%Y-%m-%d")
        results.append({
            "Keyword": keyword,
            "Title": entry.title,
            "Link": entry.link,
            "Date": pub_date,
            "Source": entry.source.title if 'source' in entry else "Google News"
        })
    return results

# --- 3. 核心函數: AI (v3.1 正式通道版) ---
def call_gemini_api(api_key, text):
    """
    使用 v1 正式版 API，並具備詳細錯誤診斷功能
    """
    # 優先使用最穩定的 Flash 模型
    model = "gemini-1.5-flash"
    
    # 改用 v1 正式版網址 (比 v1beta 更穩定)
    url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": text}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # 【關鍵修改】嘗試讀取 Google 回傳的詳細錯誤訊息
            try:
                error_info = response.json()
                error_msg = error_info.get('error', {}).get('message', 'Unknown Error')
                return f"⚠️ 失敗: {error_msg} (Code: {response.status_code})"
            except:
                return f"⚠️ 連線失敗 (Code: {response.status_code}) - 請檢查 API Key"
                
    except Exception as e:
        return f"⚠️ 程式錯誤: {str(e)}"

def ai_summarize(news_data, api_key, target_lang):
    summarized_data = []
    total = len(news_data)
    if total == 0: return []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for index, item in enumerate(news_data):
        status_text.text(f"AI Analysing: {index+1}/{total}...")
        
        prompt = f"""
        Role: Corporate PR. Summarize in 1 sentence ({target_lang}).
        News: {item['Title']}
        """
        
        summary = call_gemini_api(api_key, prompt)
        item['AI Summary'] = summary
        summarized_data.append(item)
        progress_bar.progress((index + 1) / total)
    
    status_text.empty()
    return summarized_data

# --- 4. 主執行區塊 ---
user_keywords = st.text_input(t['keywords_label'], placeholder=t['keywords_hint'])

st.markdown("---")

if st.button(t['btn_start'], type="primary"):
    if not gemini_key:
        st.error("❌ 請輸入 API Key")
    elif not user_keywords:
        st.error("❌ 請輸入關鍵字")
    else:
        st.info("🔍 正在搜尋中...")
        
        raw_news_list = []
        keywords_list = user_keywords.split(",")
        
        for kw in keywords_list:
            kw = kw.strip()
            if kw:
                results = search_google_rss(kw, time_param, t['params'])
                raw_news_list.extend(results)
        
        if not raw_news_list:
            st.warning("⚠️ 找不到相關新聞")
        else:
            final_data = ai_summarize(raw_news_list, gemini_key, t['prompt_lang'])
            df = pd.DataFrame(final_data)
            
            # 欄位排序
            cols = ["Date", "Keyword", "Title", "AI Summary", "Source", "Link"]
            df = df.reindex(columns=cols)
            
            st.dataframe(df, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
                
            st.download_button(
                label=t['download_btn'],
                data=buffer,
                file_name=f"Foxconn_News_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
