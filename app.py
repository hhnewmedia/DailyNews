import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import feedparser
import io
import urllib.parse

# --- 1. 介面與參數設定 (RSS Debug版) ---
translations = {
    "繁體中文 (TW)": {
        "title": "鴻海全球輿情監控系統 (除錯版)",
        "sidebar_title": "設定面板",
        "gemini_label": "輸入 Google Gemini API Key",
        "days_label": "搜尋時間範圍",
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
        "title": "Foxconn Media Monitor (Debug)",
        "sidebar_title": "Settings",
        "gemini_label": "Enter Gemini API Key",
        "days_label": "Search Time Range",
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
        "title": "Hệ thống Giám sát Foxconn (Debug)",
        "sidebar_title": "Cài đặt",
        "gemini_label": "Nhập Gemini API Key",
        "days_label": "Phạm vi thời gian",
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
        "title": "Monitor Foxconn (Debug)",
        "sidebar_title": "Configuración",
        "gemini_label": "Clave API Gemini",
        "days_label": "Rango de tiempo",
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
        "title": "Monitor Foxconn (Debug)",
        "sidebar_title": "Configurações",
        "gemini_label": "Chave API Gemini",
        "days_label": "Intervalo de tempo",
        "keywords_label": "Palavras-chave",
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

st.set_page_config(page_title="Foxconn RSS Debug", layout="wide")

# Sidebar
language_option = st.sidebar.selectbox("Language / 語言", list(translations.keys()))
t = translations[language_option]

st.title(f"🛠️ {t['title']}")

st.sidebar.title(t['sidebar_title'])
gemini_key_input = st.sidebar.text_input(t['gemini_label'], type="password")
# 自動去除前後空白，防止複製錯誤
gemini_key = gemini_key_input.strip() if gemini_key_input else ""

time_map = {"24 Hours / 1天": "when:1d", "Past Week / 7天": "when:7d"}
time_selection = st.sidebar.selectbox(t['days_label'], list(time_map.keys()))
time_param = time_map[time_selection]

user_keywords = st.text_input(t['keywords_label'], placeholder=t['keywords_hint'])

# --- 核心函數 ---
def search_google_rss(keyword, time_limit, params):
    base_url = "https://news.google.com/rss/search"
    query = f"{keyword} {time_limit}"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"{base_url}?q={encoded_query}&hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
    
    feed = feedparser.parse(rss_url)
    results = []
    for entry in feed.entries[:5]:
        pub_date = entry.published if 'published' in entry else datetime.now().strftime("%Y-%m-%d")
        results.append({
            "Keyword": keyword,
            "Title": entry.title,
            "Link": entry.link,
            "Date": pub_date,
            "Source": entry.source.title if 'source' in entry else "Google News"
        })
    return results

def ai_summarize(news_data, api_key, lang_selection):
    # 使用最新的 Flash 模型
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    target_lang = lang_selection.split("(")[0].strip()
    
    summarized_data = []
    total = len(news_data)
    if total == 0: return []
    
    progress_bar = st.progress(0)
    
    for index, item in enumerate(news_data):
        try:
            prompt = f"""
            Task: Provide a brief summary for a corporate report based on this news headline.
            Target Language: {target_lang}
            Limit: 1-2 sentences.
            
            News Title: {item['Title']}
            News Link: {item['Link']}
            """
            response = model.generate_content(prompt)
            summary = response.text
        except Exception as e:
            # 這裡會把真正的錯誤原因抓出來
            error_msg = str(e)
            if "400" in error_msg:
                summary = "Error: Key 無效或請求錯誤 (400)"
            elif "403" in error_msg:
                summary = "Error: 權限不足 (403) - 請檢查 Key 是否啟用"
            elif "429" in error_msg:
                summary = "Error: 額度已滿 (429)"
            elif "not found" in error_msg:
                summary = "Error: 模型版本不符 (Model Not Found)"
            else:
                summary = f"Error: {error_msg}"
            
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
            st.warning("No news found. / 找不到相關新聞")
        else:
            final_data = ai_summarize(raw_news_list, gemini_key, language_option)
            df = pd.DataFrame(final_data)
            
            # 確保欄位順序
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
