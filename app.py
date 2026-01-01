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
        "gemini_label": "輸入 Gemini API Key (選填)",
        "gemini_help": "若不輸入，程式將只執行搜尋與匯出功能",
        "days_label": "搜尋時間範圍 (天數)",
        "keywords_label": "輸入搜尋關鍵字",
        "keywords_hint": "例如: 鴻海, Fii, 電動車",
        "btn_start": "開始搜尋與分析",
        "download_btn": "下載 Excel 報表",
        "params": {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
        "prompt_lang": "Traditional Chinese"
    },
    "English (US)": {
        "title": "Foxconn Media Monitor",
        "sidebar_title": "Settings",
        "gemini_label": "Enter Gemini API Key (Optional)",
        "gemini_help": "If empty, only search and export will run",
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
        "gemini_label": "Nhập Gemini API Key (Tùy chọn)",
        "gemini_help": "Nếu trống, chỉ tìm kiếm và xuất báo cáo",
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
        "gemini_label": "Clave API Gemini (Opcional)",
        "gemini_help": "Si está vacío, solo busca y exporta",
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
        "gemini_label": "Chave API Gemini (Opcional)",
        "gemini_help": "Se vazio, apenas pesquisa e exporta",
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
# 這裡設為選填，不強迫輸入
gemini_key_input = st.sidebar.text_input(t['gemini_label'], type="password", help=t['gemini_help'])
gemini_key = gemini_key_input.strip() if gemini_key_input else ""

days_selected = st.sidebar.slider(t['days_label'], 1, 7, 1)
time_param = f"when:{days_selected}d"

st.sidebar.markdown("---")
st.sidebar.success("✅ System Ready (v5.0 Safe Mode)")

# --- 2. 核心搜尋 ---
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

# --- 3. AI 呼叫 (安全防護版) ---
def call_gemini_api(api_key, text):
    if not api_key:
        return ""
        
    # 改用最穩定的 v1 正式版網址，並使用 gemini-pro (相容性最高)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": text}]}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=8)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # 若失敗，不顯示錯誤代碼嚇人，直接回傳空字串或提示
            return "(AI 權限受限，僅顯示標題)" 
    except:
        return "(連線逾時)"

def process_news(news_data, api_key, target_lang):
    final_data = []
    total = len(news_data)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for index, item in enumerate(news_data):
        # 如果有 Key 才做 AI，沒 Key 直接跳過
        if api_key:
            status_text.text(f"Processing: {index+1}/{total}...")
            prompt = f"Role: PR. Summarize in 1 sentence ({target_lang}). News: {item['Title']}"
            summary = call_gemini_api(api_key, prompt)
        else:
            summary = "" # 沒 Key 就留空，保持版面乾淨
            
        item['AI Summary'] = summary
        final_data.append(item)
        progress_bar.progress((index + 1) / total)
    
    status_text.empty()
    return final_data

# --- 4. 主程式 ---
user_keywords = st.text_input(t['keywords_label'], placeholder=t['keywords_hint'])

st.markdown("---")

if st.button(t['btn_start'], type="primary"):
    if not user_keywords:
        st.error("❌ 請輸入關鍵字")
    else:
        # 就算沒 Key 也讓他跑
        st.info("🔍 搜尋中...")
        
        raw_news_list = []
        keywords
