import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import feedparser
import io
import urllib.parse
import time

# --- 1. 介面與參數設定 (RSS 最終修復版) ---
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
        "params": {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"}
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
        "params": {"hl": "en-US", "gl": "US", "ceid": "US:en"}
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
        "params": {"hl": "vi", "gl": "VN", "ceid": "VN:vi"}
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
        "params": {"hl": "es-419", "gl": "MX", "ceid": "MX:es-419"}
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
        "params": {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"}
    }
}

st.set_page_config(page_title="Foxconn RSS Monitor", layout="wide")

# Sidebar
language_option = st.sidebar.selectbox("Language / 語言", list(translations.keys()))
t = translations[language_option]

st.title(f"📰 {t['title']}")

st.sidebar.title(t['sidebar_title'])
gemini_key_input = st.sidebar.text_input(t['gemini_label'], type="password")
gemini_key = gemini_key_input.strip() if gemini_key_input else ""

# --- 更新功能：天數選擇 (1~7天) ---
# 使用 slider 讓使用者選擇 1 到 7，預設為 1
days_selected = st.sidebar.slider(
    t['days_label'],
    min_value=1,
    max_value=7,
    value=1
)
# 轉換成 Google RSS 需要的格式 (例如 when:1d)
time_param = f"when:{days_selected}d"

user_keywords = st.text_input(t['keywords_label'], placeholder=t['keywords_hint'])

# --- 核心函數 ---
def search_google_rss(keyword, time_limit, params):
    base_url = "https://news.google.com/rss/search"
    query = f"{keyword} {time_limit}"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"{base_url}?q={encoded_query}&hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
    
    feed = feedparser.parse(rss_url)
    results = []
    # 稍微增加數量，取前 10 篇以免漏掉
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

def get_ai_response(model_name, prompt):
    """嘗試使用指定的模型獲取回應"""
    model = genai.GenerativeModel(model_name)
    return model.generate_content(prompt)

def ai_summarize(news_data, api_key, lang_selection):
    genai.configure(api_key=api_key)
    target_lang = lang_selection.split("(")[0].strip()
    
    summarized_data = []
    total = len(news_data)
    if total == 0: return []
    
    progress_bar = st.progress(0)
    
    for index, item in enumerate(news_data):
        prompt = f"""
        Task: You are a PR assistant for Foxconn. Summarize this news headline in 1 sentence.
        Target Language: {target_lang}
        
        News Title: {item['Title']}
        News Link: {item['Link']}
        """
        
        summary = ""
        try:
            # 優先嘗試快速版模型 (Flash)
            response = get_ai_response('gemini-1.5-flash', prompt)
            summary = response.text
        except Exception as e:
            # 如果失敗 (例如 Model Not Found)，自動切換回穩定版 (Pro)
            try:
                response = get_ai_response('gemini-pro', prompt)
                summary = response.text
            except Exception as e2:
                # 真的不行才報錯
                error_msg = str(e2)
                if "429" in error_msg:
                    summary = "Error: 額度已滿 (請稍後再試)"
                else:
                    summary = f"AI Error: {error_msg}"
            
        item['AI Summary'] = summary
        summarized_data.append(item)
        progress_bar.progress((index + 1) / total)
        
    return summarized_data

# --- 執行邏輯 ---
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
                results = search_google_rss(kw, time_param, t['params'])
                raw_news_list.extend(results)
        
        if not raw_news_list:
            st.warning(f"No news found in the past {days_selected} days.")
        else:
            final_data = ai_summarize(raw_news_list, gemini_key, language_option)
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
