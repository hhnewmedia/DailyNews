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
        "model_label": "選擇 AI 模型 (若失敗請換一個)",
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
        "model_label": "Select AI Model",
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
        "model_label": "Chọn mô hình AI",
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
        "model_label": "Seleccionar modelo AI",
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
        "sidebar_title": "Configurações
