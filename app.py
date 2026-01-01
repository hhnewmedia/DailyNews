import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
import io
import urllib.parse
import time

# --- 1. 設定與翻譯 ---
translations = {
    "繁體中文 (TW)": {
        "title": "鴻海全球輿情監控系統",
        "sidebar_title": "設定面板",
        "days_label": "搜尋時間範圍 (天數)",
        "keywords_label": "輸入搜尋關鍵字 (多組請用逗號隔開)",
        "keywords_hint": "建議輸入: 鴻海, Foxconn, 富士康, Fii, 鴻華先進",
        "btn_start": "開始全網搜尋",
        "download_btn": "下載 Excel 報表",
        "params": {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"}
    },
    "English (US)": {
        "title": "Foxconn Media Monitor",
        "sidebar_title": "Settings",
        "days_label": "Search Range (Days)",
        "keywords_label": "Enter Keywords",
        "keywords_hint": "e.g., Foxconn, Fii, EV",
        "btn_start": "Start Search",
        "download_btn": "Download Excel",
        "params": {"hl": "en-US", "gl": "US", "ceid": "US:en"}
    },
    "Tiếng Việt (VN)": {
        "title": "Hệ thống Giám sát Foxconn",
        "sidebar_title": "Cài đặt",
        "days_label": "Phạm vi thời gian",
        "keywords_label": "Nhập từ khóa",
        "keywords_hint": "Ví dụ: Foxconn, Fii",
        "btn_start": "Bắt đầu tìm kiếm",
        "download_btn": "Tải xuống báo cáo",
        "params": {"hl": "vi", "gl": "VN", "ceid": "VN:vi"}
    },
    "Español (MX)": {
        "title": "Monitor Foxconn",
        "sidebar_title": "Configuración",
        "days_label": "Rango de tiempo",
        "keywords_label": "Palabras clave",
        "keywords_hint": "Ej: Foxconn, Fii",
        "btn_start": "Iniciar búsqueda",
        "download_btn": "Descargar Excel",
        "params": {"hl": "es-419", "gl": "MX", "ceid": "MX:es-419"}
    },
    "Português (BR)": {
        "title": "Monitor Foxconn",
        "sidebar_title": "Configurações",
        "days_label": "Intervalo de tempo",
        "keywords_label": "Palabras-chave",
        "keywords_hint": "Ex: Foxconn, Fii",
        "btn_start": "Iniciar pesquisa",
        "download_btn": "Baixar Excel",
        "params": {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"}
    }
}

st.set_page_config(page_title="Foxconn Search Pro", layout="wide")

# Sidebar
language_option = st.sidebar.selectbox("Language / 語言", list(translations.keys()))
t = translations[language_option]

st.title(f"🔍 {t['title']}")

st.sidebar.title(t['sidebar_title'])

# 天數滑桿 (1-7天)
days_selected = st.sidebar.slider(t['days_label'], 1, 7, 1)
time_param = f"when:{days_selected}d"

st.sidebar.markdown("---")
st.sidebar.info("💡 提示：輸入越多關鍵字，搜尋結果越完整。\n例如：`鴻海, Foxconn, 富士康`")

# --- 2. 核心搜尋引擎 (無限制版) ---
def search_google_rss(keyword, time_limit, params):
    # Google News RSS URL
    base_url = "https://news.google.com/rss/search"
    query = f"{keyword} {time_limit}"
    encoded_query = urllib.parse.quote(query)
    
    # 組合 RSS 網址
    rss_url = f"{base_url}?q={encoded_query}&hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
    
    # 讀取 RSS
    feed = feedparser.parse(rss_url)
    
    results = []
    # 【關鍵修改】這裡不再使用 [:10] 限制，改為讀取所有 feed.entries
    for entry in feed.entries:
        # 處理發布時間格式
        if 'published_parsed' in entry:
            pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")
        else:
            pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        results.append({
            "Date": pub_date,
            "Keyword": keyword,
            "Title": entry.title,
            "Source": entry.source.title if 'source' in entry else "Google News",
            "Link": entry.link
        })
    return results

# --- 3. 主程式 ---
user_keywords = st.text_input(t['keywords_label'], placeholder=t['keywords_hint'])

if st.button(t['btn_start'], type="primary"):
    if not user_keywords:
        st.error("❌ 請至少輸入一個關鍵字")
    else:
        st.info("🚀 全網搜尋中，請稍候...")
        
        raw_news_list = []
        keywords_list = user_keywords.split(",")
        
        # 進度條
        progress_bar = st.progress(0)
        total_kw = len(keywords_list)
        
        for idx, kw in enumerate(keywords_list):
            kw = kw.strip()
            if kw:
                results = search_google_rss(kw, time_param, t['params'])
                raw_news_list.extend(results)
            # 更新進度
            progress_bar.progress((idx + 1) / total_kw)
        
        if not raw_news_list:
            st.warning("⚠️ 在指定時間內找不到相關新聞。建議：\n1. 增加天數範圍\n2. 增加關鍵字 (如: Foxconn, 富士康)")
        else:
            # 轉為 DataFrame
            df = pd.DataFrame(raw_news_list)
            
            # 【關鍵修改】去重功能
            # 有時候不同關鍵字會搜到同一篇新聞，這裡用「連結」來去除重複
            initial_count = len(df)
            df = df.drop_duplicates(subset=['Link'])
            final_count = len(df)
            
            # 排序：按日期由新到舊
            df = df.sort_values(by='Date', ascending=False)
            
            # 顯示統計
            st.success(f"✅ 搜尋完成！共找到 {final_count} 篇新聞 (已過濾重複 {initial_count - final_count} 篇)")
            
            # 顯示表格 (調整欄位順序)
            cols = ["Date", "Keyword", "Title", "Source", "Link"]
            df = df[cols]
            
            # 使用 container_width 讓表格填滿畫面，並設定連結欄位可點擊
            st.dataframe(
                df, 
                use_container_width=True,
                column_config={
                    "Link": st.column_config.LinkColumn("News Link")
                }
            )
            
            # 下載 Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
                
            st.download_button(
                label=t['download_btn'],
                data=buffer,
                file_name=f"Foxconn_News_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )
