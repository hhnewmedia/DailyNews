import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import feedparser
import io
import urllib.parse
from bs4 import BeautifulSoup

# --- 1. 介面與參數設定 (RSS 免費版) ---
# 這裡設定了各國對應的 Google News 參數，確保搜到當地新聞
translations = {
    "繁體中文 (TW)": {
        "title": "鴻海全球輿情監控系統 (RSS版)",
        "sidebar_title": "設定面板",
        "gemini_label": "輸入 Google Gemini API Key (AI 摘要用)",
        "days_label": "搜尋時間範圍",
        "keywords_label": "輸入搜尋關鍵字 (用逗號隔開)",
        "keywords_hint": "例如: 鴻海, Fii, 電動車",
        "btn_start": "開始搜尋與分析",
        "processing": "正在讀取 Google News RSS 並進行 AI 摘要...",
        "success": "分析完成！",
        "download_btn": "下載 Excel 報表",
        "error_api": "請輸入 Gemini API Key 才能使用 AI 摘要！",
        "error_no_key": "請輸入至少一個關鍵字！",
        "params": {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"} # 台灣參數
    },
    "English (US)": {
        "title": "Foxconn Media Monitor (RSS Ed.)",
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
        "params": {"hl": "en-US", "gl": "US", "ceid": "US:en"} # 美國參數
    },
    "Tiếng Việt (VN)": {
        "title": "Hệ thống Giám sát Foxconn (RSS)",
        "sidebar_title": "Cài đặt",
        "gemini_label": "Nhập Gemini API Key",
        "days_label": "Phạm vi thời gian",
        "keywords_label": "Nhập từ khóa (phân cách dấu phẩy)",
        "keywords_hint": "Ví dụ: Foxconn, Fii",
        "btn_start": "Bắt đầu tìm kiếm",
        "processing": "Đang tải tin tức...",
        "success": "Hoàn tất!",
        "download_btn": "Tải xuống báo cáo",
        "error_api": "Vui lòng nhập API Key!",
        "error_no_key": "Vui lòng nhập từ khóa!",
        "params": {"hl": "vi", "gl": "VN", "ceid": "VN:vi"} # 越南參數
    },
    "Español (MX)": {
        "title": "Monitor Foxconn (RSS)",
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
        "params": {"hl": "es-419", "gl": "MX", "ceid": "MX:es-419"} # 墨西哥參數
    },
    "Português (BR)": {
        "title": "Monitor Foxconn (RSS)",
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
        "params": {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"} # 巴西參數
    }
}

st.set_page_config(page_title="Foxconn RSS Monitor", layout="wide")

# Sidebar
language_option = st.sidebar.selectbox("Language / 語言", list(translations.keys()))
t = translations[language_option]

st.title(f"📡 {t['title']}")

st.sidebar.title(t['sidebar_title'])
gemini_key = st.sidebar.text_input(t['gemini_label'], type="password")

# 時間範圍：RSS 使用 when:7d 這種語法
time_map = {"24 Hours / 1天": "when:1d", "Past Week / 7天": "when:7d"}
time_selection = st.sidebar.selectbox(t['days_label'], list(time_map.keys()))
time_param = time_map[time_selection]

# Main Input
user_keywords = st.text_input(t['keywords_label'], placeholder=t['keywords_hint'])

# --- 4. 核心函數: Google RSS Feed ---
def search_google_rss(keyword, time_limit, params):
    """
    使用 Google News RSS Feed 獲取資料
    這是一個公開的資料流，不需要 API Key，且比爬蟲穩定
    """
    # 組合搜尋網址
    # 格式: https://news.google.com/rss/search?q={關鍵字}+{時間}&hl={語言}&gl={地區}&ceid={地區:語言}
    base_url = "https://news.google.com/rss/search"
    
    # URL Encode 關鍵字
    query = f"{keyword} {time_limit}"
    encoded_query = urllib.parse.quote(query)
    
    rss_url = f"{base_url}?q={encoded_query}&hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
    
    # 解析 RSS
    feed = feedparser.parse(rss_url)
    
    results = []
    # 取前 5 篇
    for entry in feed.entries[:5]:
        # 清理標題 (有時候標題會包含來源，如 'Foxconn news - Reuters')
        clean_title = entry.title
        
        # 嘗試解析發布時間
        pub_date = entry.published if 'published' in entry else datetime.now().strftime("%Y-%m-%d")
        
        results.append({
            "Keyword": keyword,
            "Title": clean_title,
            "Link": entry.link,
            "Date": pub_date,
            "Source": entry.source.title if 'source' in entry else "Google News"
        })
        
    return results

def ai_summarize(news_data, api_key, lang_selection):
    """Gemini AI 摘要"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    target_lang = lang_selection.split("(")[0].strip()
    
    summarized_data = []
    total = len(news_data)
    if total == 0: return []
    
    progress_bar = st.progress(0)
    
    for index, item in enumerate(news_data):
        try:
            # RSS 有時候沒有內文預覽，我們用標題請 AI 擴寫或嘗試總結
            prompt = f"""
            Task: Provide a brief summary for a corporate report based on this news headline.
            Target Language: {target_lang}
            Limit: 1-2 sentences.
            
            News Title: {item['Title']}
            News Link: {item['Link']}
            (Note: Since I cannot browse the link, summarize based on the title's implication for Foxconn/Business.)
            """
            response = model.generate_content(prompt)
            summary = response.text
        except:
            summary = "AI processing failed."
            
        item['AI Summary'] = summary
        summarized_data.append(item)
        progress_bar.progress((index + 1) / total)
        
    return summarized_data

# --- 5. 執行邏輯 ---
if st.button(t['btn_start'], type="primary"):
    if not gemini_key:
        st.error(t['error_api'])
    elif not user_keywords:
        st.error(t['error_no_key'])
    else:
        st.info(t['processing'])
        
        raw_news_list = []
        keywords_list = user_keywords.split(",")
        
        # 1. 執行 RSS 搜尋
        for kw in keywords_list:
            kw = kw.strip()
            if kw:
                results = search_google_rss(kw, time_param, t['params'])
                raw_news_list.extend(results)
        
        if not raw_news_list:
            st.warning("No news found. / 找不到相關新聞 (RSS)")
        else:
            # 2. AI 摘要
            final_data = ai_summarize(raw_news_list, gemini_key, language_option)
            
            # 3. 顯示與下載
            df = pd.DataFrame(final_data)
            
            # 調整欄位順序
            cols = ["Date", "Keyword", "Title", "AI Summary", "Source", "Link"]
            # 確保欄位存在 (防止 AI 出錯時缺欄位)
            df = df.reindex(columns=cols)
            
            st.dataframe(df, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
                
            st.download_button(
                label=t['download_btn'],
                data=buffer,
                file_name=f"Foxconn_News_RSS_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
