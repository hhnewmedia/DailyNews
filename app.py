import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import io
import urllib.parse
import requests
import json

# --- 1. 多國語言與參數設定 (完全體) ---
translations = {
    "繁體中文 (TW)": {
        "title": "鴻海全球輿情監控系統",
        "sidebar_title": "設定面板",
        "gemini_label": "輸入 Google Gemini API Key",
        "days_label": "搜尋時間範圍 (天數)",
        "keywords_label": "輸入搜尋關鍵字 (用逗號隔開)",
        "keywords_hint": "例如: 鴻海, Fii, 電動車",
        "btn_start": "開始搜尋與分析",
        "processing": "正在讀取 Google News RSS 並進行 AI 摘要...",
        "success": "分析完成！",
        "download_btn": "下載 Excel 報表",
        "error_api": "請輸入 Gemini API Key 才能使用 AI 摘要！",
        "error_no_key": "請輸入至少一個關鍵字！",
        "params": {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
        "prompt_lang": "Traditional Chinese"
    },
    "English (US)": {
        "title": "Foxconn Media Monitor",
        "sidebar_title": "Settings",
        "gemini_label": "Enter Gemini API Key",
        "days_label": "Search Range (Days)",
        "keywords_label": "Enter Keywords (separated by comma)",
        "keywords_hint": "e.g., Foxconn, Fii, EV",
        "btn_start": "Start Search",
        "processing": "Fetching Google News RSS...",
        "success": "Analysis Complete!",
        "download_btn": "Download Excel",
        "error_api": "Please enter Gemini API Key!",
        "error_no_key": "Please enter keywords!",
        "params": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
        "prompt_lang": "English"
    },
    "Tiếng Việt (VN)": {
        "title": "Hệ thống Giám sát Foxconn",
        "sidebar_title": "Cài đặt",
        "gemini_label": "Nhập Gemini API Key",
        "days_label": "Phạm vi thời gian (Ngày)",
        "keywords_label": "Nhập từ khóa",
        "keywords_hint": "Ví dụ: Foxconn, Fii",
        "btn_start": "Bắt đầu tìm kiếm",
        "processing": "Đang tải tin tức...",
        "success": "Hoàn tất!",
        "download_btn": "Tải xuống báo cáo",
        "error_api": "Vui lòng nhập API Key!",
        "error_no_key": "Vui lòng nhập từ khóa!",
        "params": {"hl": "vi", "gl": "VN", "ceid": "VN:vi"},
        "prompt_lang": "Vietnamese"
    },
    "Español (MX)": {
        "title": "Monitor Foxconn",
        "sidebar_title": "Configuración",
        "gemini_label": "Clave API Gemini",
        "days_label": "Rango de tiempo (Días)",
        "keywords_label": "Palabras clave",
        "keywords_hint": "Ej: Foxconn, Fii",
        "btn_start": "Iniciar búsqueda",
        "processing": "Cargando noticias...",
        "success": "¡Completo!",
        "download_btn": "Descargar Excel",
        "error_api": "¡Ingrese clave API!",
        "error_no_key": "¡Ingrese palabras clave!",
        "params": {"hl": "es-419", "gl": "MX", "ceid": "MX:es-419"},
        "prompt_lang": "Spanish"
    },
    "Português (BR)": {
        "title": "Monitor Foxconn",
        "sidebar_title": "Configurações",
        "gemini_label": "Chave API Gemini",
        "days_label": "Intervalo de tempo (Dias)",
        "keywords_label": "Palabras-chave",
        "keywords_hint": "Ex: Foxconn, Fii",
        "btn_start": "Iniciar pesquisa",
        "processing": "Carregando notícias...",
        "success": "Concluído!",
        "download_btn": "Baixar Excel",
        "error_api": "Insira a chave API!",
        "error_no_key": "Insira palavras-chave!",
        "params": {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
        "prompt_lang": "Portuguese"
    }
}

st.set_page_config(page_title="Foxconn Global Monitor", layout="wide")

# Sidebar - 語言選擇
language_option = st.sidebar.selectbox("Language / 語言", list(translations.keys()))
t = translations[language_option]

st.title(f"🦊 {t['title']}")

st.sidebar.title(t['sidebar_title'])
gemini_key_input = st.sidebar.text_input(t['gemini_label'], type="password")
gemini_key = gemini_key_input.strip() if gemini_key_input else ""

# 天數滑桿
days_selected = st.sidebar.slider(t['days_label'], 1, 7, 1)
time_param = f"when:{days_selected}d"

user_keywords = st.text_input(t['keywords_label'], placeholder=t['keywords_hint'])

# --- 2. 核心函數: Google News RSS 搜尋 ---
def search_google_rss(keyword, time_limit, params):
    base_url = "https://news.google.com/rss/search"
    query = f"{keyword} {time_limit}"
    encoded_query = urllib.parse.quote(query)
    
    # 使用選擇的語言參數 (hl, gl, ceid)
    rss_url = f"{base_url}?q={encoded_query}&hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
    
    feed = feedparser.parse(rss_url)
    results = []
    for entry in feed.entries[:10]: # 取前10篇
        pub_date = entry.published if 'published' in entry else datetime.now().strftime("%Y-%m-%d")
        results.append({
            "Keyword": keyword,
            "Title": entry.title,
            "Link": entry.link,
            "Date": pub_date,
            "Source": entry.source.title if 'source' in entry else "Google News"
        })
    return results

# --- 3. 核心函數: AI 摘要 (REST API - 穩定版) ---
def call_gemini_api(api_key, text):
    """直接呼叫 Google API，避開套件版本問題"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": text}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # 若 Flash 失敗，嘗試 Pro
            url_pro = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            response_pro = requests.post(url_pro, headers=headers, data=json.dumps(payload))
            if response_pro.status_code == 200:
                return response_pro.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def ai_summarize(news_data, api_key, target_lang):
    summarized_data = []
    total = len(news_data)
    if total == 0: return []
    
    progress_bar = st.progress(0)
    
    for index, item in enumerate(news_data):
        # 動態提示詞：根據選擇的語言要求 AI 回覆
        prompt = f"""
        Role: Corporate PR Assistant.
        Task: Summarize this news headline in 1 sentence.
        Target Language: {target_lang}
        
        News Title: {item['Title']}
        """
        
        summary = call_gemini_api(api_key, prompt)
            
        item['AI Summary'] = summary
        summarized_data.append(item)
        progress_bar.progress((index + 1) / total)
        
    return summarized_data

# --- 4. 執行邏輯 ---
if st.button(t['btn_start'], type="primary"):
    if not gemini_key:
        st.error(t['error_api'])
    elif not user_keywords:
        st.error(t['error_no_key'])
    else:
        st.info(t['processing'])
        
        raw_news_list = []
        keywords_list = user_keywords.split(",")
        
        for kw in keywords_list:
            kw = kw.strip()
            if kw:
                # 傳入語言參數
                results = search_google_rss(kw, time_param, t['params'])
                raw_news_list.extend(results)
        
        if not raw_news_list:
            st.warning("No news found / 找不到相關新聞")
        else:
            # 傳入目標語言
            final_data = ai_summarize(raw_news_list, gemini_key, t['prompt_lang'])
            df = pd.DataFrame(final_data)
            
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
