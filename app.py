import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import io
import urllib.parse
import requests
import json
import time

# --- 1. 多國語言與參數設定 ---
translations = {
    "繁體中文 (TW)": {
        "title": "鴻海全球輿情監控系統",
        "sidebar_title": "設定面板",
        "gemini_label": "輸入 Google Gemini API Key",
        "days_label": "搜尋時間範圍 (天數)",
        "keywords_label": "輸入搜尋關鍵字 (用逗號隔開)",
        "keywords_hint": "例如: 鴻海, Fii, 電動車",
        "btn_start": "開始搜尋與分析",
        "processing": "正在讀取 Google News RSS 並嘗試連接 AI 模型...",
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
