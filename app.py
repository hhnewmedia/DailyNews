import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import feedparser
import io
import urllib.parse
import sys

# --- 1. 介面與參數設定 (最終鎖定版) ---
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
    # ... (為節省篇幅，其他語言會自動沿用之前的邏輯，或是您可以只保留中文版測試) ...
}
# 為了避免程式碼過長，這裡使用簡易版的多國語言切換
# 如果您需要完整的五國語言，請保留您原本的 translations 字典，只需更新下方的 ai_summarize 函數即可
# 但為了確保您現在能成功，我下面放的是核心邏輯修復版

st.set_page_config(page_title="Foxconn RSS Monitor", layout="wide")

st.title("🦊 鴻海全球輿情監控系統")

# Sidebar
st.sidebar.title("設定面板")
gemini_key_input = st.sidebar.text_input("輸入 Google Gemini API Key", type="password")
gemini_key = gemini_key_input.strip() if gemini_key_input else ""

# 天數滑桿
days_selected = st.sidebar.slider("搜尋時間範圍 (天數)", 1, 7, 1)
time_param = f"when:{days_selected}d"

user_keywords = st.text_input("輸入搜尋關鍵字 (用逗號隔開)", placeholder="例如: 鴻海, Fii, 電動車")

# --- 核心函數 ---
def search_google_rss(keyword, time_limit, params):
    base_url = "https://news.google.com/rss/search"
    query = f"{keyword} {time_limit}"
    encoded_query = urllib.parse.quote(query)
    # 預設使用台灣繁體中文搜尋，若需多國語言可再擴充
    rss_url = f"{base_url}?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
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

def ai_summarize(news_data, api_key):
    # 強制使用 gemini-1.5-flash
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    summarized_data = []
    total = len(news_data)
    if total == 0: return []
    
    progress_bar = st.progress(0)
    
    for index, item in enumerate(news_data):
        summary = ""
        try:
            prompt = f"""
            Task: Summarize this news headline in 1 sentence (Traditional Chinese).
            News Title: {item['Title']}
            News Link: {item['Link']}
            """
            response = model.generate_content(prompt)
            summary = response.text
        except Exception as e:
            # 這裡會印出詳細錯誤，方便除錯
            summary = f"Error: {str(e)}"
            
        item['AI Summary'] = summary
        summarized_data.append(item)
        progress_bar.progress((index + 1) / total)
        
    return summarized_data

# --- 執行邏輯 ---
if st.button("開始搜尋與分析", type="primary"):
    if not gemini_key:
        st.error("請輸入 API Key")
    elif not user_keywords:
        st.error("請輸入關鍵字")
    else:
        st.info("正在執行...")
        
        raw_news_list = []
        keywords_list = user_keywords.split(",")
        
        for kw in keywords_list:
            kw = kw.strip()
            if kw:
                results = search_google_rss(kw, time_param, {})
                raw_news_list.extend(results)
        
        if not raw_news_list:
            st.warning("找不到新聞")
        else:
            final_data = ai_summarize(raw_news_list, gemini_key)
            df = pd.DataFrame(final_data)
            
            cols = ["Date", "Keyword", "Title", "AI Summary", "Source", "Link"]
            df = df.reindex(columns=cols)
            
            st.dataframe(df, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
                
            st.download_button(
                label="下載 Excel 報表",
                data=buffer,
                file_name=f"Foxconn_News.xlsx",
                mime="application/vnd.ms-excel"
            )
