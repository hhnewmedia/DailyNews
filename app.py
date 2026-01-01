import streamlit as st
from duckduckgo_search import DDGS
import google.generativeai as genai
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. 介面語言設定 (UI Translations) ---
translations = {
    "繁體中文 (TW)": {
        "title": "鴻海全球輿情監控系統",
        "sidebar_title": "設定面板",
        "lang_select": "選擇介面語言",
        "api_label": "輸入 Google Gemini API Key",
        "days_label": "搜尋時間範圍",
        "keywords_label": "輸入搜尋關鍵字 (用逗號隔開)",
        "keywords_hint": "例如: 鴻海, Fii, 電動車",
        "btn_start": "開始搜尋與分析",
        "processing": "正在搜尋新聞並進行 AI 摘要，這需要一點時間...",
        "success": "分析完成！",
        "col_title": "新聞標題",
        "col_summary": "AI 重點摘要",
        "col_link": "連結",
        "col_date": "日期",
        "download_btn": "下載 Excel 報表",
        "error_api": "請先輸入 API Key 才能使用 AI 功能！",
        "error_no_key": "請輸入至少一個關鍵字！"
    },
    "English (US)": {
        "title": "Foxconn Global Media Monitor",
        "sidebar_title": "Settings",
        "lang_select": "Interface Language",
        "api_label": "Enter Google Gemini API Key",
        "days_label": "Search Time Range",
        "keywords_label": "Enter Keywords (separated by comma)",
        "keywords_hint": "e.g., Foxconn, Fii, EV",
        "btn_start": "Start Search & Analysis",
        "processing": "Searching and generating AI summaries...",
        "success": "Analysis Complete!",
        "col_title": "Title",
        "col_summary": "AI Summary",
        "col_link": "Link",
        "col_date": "Date",
        "download_btn": "Download Excel Report",
        "error_api": "Please enter API Key first!",
        "error_no_key": "Please enter at least one keyword!"
    },
    "Tiếng Việt (VN)": {
        "title": "Hệ thống Giám sát Truyền thông Toàn cầu Foxconn",
        "sidebar_title": "Cài đặt",
        "lang_select": "Ngôn ngữ giao diện",
        "api_label": "Nhập Google Gemini API Key",
        "days_label": "Phạm vi thời gian tìm kiếm",
        "keywords_label": "Nhập từ khóa (phân cách bằng dấu phẩy)",
        "keywords_hint": "Ví dụ: Foxconn, Fii, Xe điện",
        "btn_start": "Bắt đầu tìm kiếm & Phân tích",
        "processing": "Đang tìm kiếm và tạo tóm tắt AI...",
        "success": "Hoàn tất phân tích!",
        "col_title": "Tiêu đề",
        "col_summary": "Tóm tắt AI",
        "col_link": "Liên kết",
        "col_date": "Ngày",
        "download_btn": "Tải xuống báo cáo Excel",
        "error_api": "Vui lòng nhập API Key trước!",
        "error_no_key": "Vui lòng nhập ít nhất một từ khóa!"
    },
    "Español (MX)": {
        "title": "Monitor Global de Medios de Foxconn",
        "sidebar_title": "Configuración",
        "lang_select": "Idioma de la interfaz",
        "api_label": "Ingrese Google Gemini API Key",
        "days_label": "Rango de tiempo de búsqueda",
        "keywords_label": "Ingrese palabras clave (separadas por comas)",
        "keywords_hint": "Ej: Foxconn, Fii, Vehículos eléctricos",
        "btn_start": "Iniciar búsqueda y análisis",
        "processing": "Buscando y generando resúmenes de IA...",
        "success": "¡Análisis completo!",
        "col_title": "Título",
        "col_summary": "Resumen IA",
        "col_link": "Enlace",
        "col_date": "Fecha",
        "download_btn": "Descargar informe Excel",
        "error_api": "¡Ingrese la clave API primero!",
        "error_no_key": "¡Ingrese al menos una palabra clave!"
    },
     "Português (BR)": {
        "title": "Monitor Global de Mídia da Foxconn",
        "sidebar_title": "Configurações",
        "lang_select": "Idioma da interface",
        "api_label": "Insira Google Gemini API Key",
        "days_label": "Intervalo de tempo de pesquisa",
        "keywords_label": "Insira palavras-chave (separadas por vírgula)",
        "keywords_hint": "Ex: Foxconn, Fii, Veículos elétricos",
        "btn_start": "Iniciar pesquisa e análise",
        "processing": "Pesquisando e gerando resumos de IA...",
        "success": "Análise concluída!",
        "col_title": "Título",
        "col_summary": "Resumo IA",
        "col_link": "Link",
        "col_date": "Data",
        "download_btn": "Baixar relatório Excel",
        "error_api": "Por favor, insira a chave da API primeiro!",
        "error_no_key": "Por favor, insira pelo menos uma palavra-chave!"
    }
}

# --- 2. 應用程式設定 ---
st.set_page_config(page_title="Foxconn Media Monitor", layout="wide")

# Sidebar - 語言選擇
language_option = st.sidebar.selectbox(
    "Language / 語言",
    list(translations.keys())
)
t = translations[language_option]

st.title(f"🦊 {t['title']}")
st.markdown("---")

# Sidebar - API Key 與 設定
st.sidebar.title(t['sidebar_title'])
api_key = st.sidebar.text_input(t['api_label'], type="password")

# 時間範圍對應 DuckDuckGo 參數 (d=1天, w=1週)
time_map = {
    "24 Hours / 1天": "d",
    "Past Week / 7天": "w"
}
time_selection = st.sidebar.selectbox(t['days_label'], list(time_map.keys()))
ddg_time_param = time_map[time_selection]

# --- 3. 主畫面輸入 ---
user_keywords = st.text_input(t['keywords_label'], placeholder=t['keywords_hint'])

# --- 4. 核心功能函數 ---

def search_news(keywords_list, time_limit):
    """使用 DuckDuckGo 搜尋新聞"""
    results = []
    with DDGS() as ddgs:
        for keyword in keywords_list:
            keyword = keyword.strip()
            if not keyword: continue
            # 搜尋新聞，限制時間與數量
            news_gen = ddgs.news(keyword, region="wt-wt", safesearch="off", timelimit=time_limit, max_results=5)
            if news_gen:
                for r in news_gen:
                    results.append({
                        "Keyword": keyword,
                        "Title": r.get('title'),
                        "Link": r.get('url'),
                        "Date": r.get('date'),
                        "Source": r.get('source'),
                        "Snippet": r.get('body') # 這是搜尋引擎抓到的預覽文字
                    })
            time.sleep(0.5) # 稍微暫停避免太快
    return results

def ai_summarize(news_data, api_key, lang_selection):
    """使用 Gemini AI 進行摘要"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    # 決定 AI 回覆的語言
    target_lang = lang_selection.split("(")[0].strip() # 抓取中文、English等字眼

    summarized_data = []
    total = len(news_data)
    
    progress_bar = st.progress(0)
    
    for index, item in enumerate(news_data):
        try:
            # 提示詞工程：要求 AI 扮演專業公關
            prompt = f"""
            Task: Summarize the following news snippet related to Foxconn/business for a corporate PR report.
            Target Language: {target_lang}
            Limit: Within 50 words.
            
            News Title: {item['Title']}
            News Snippet: {item['Snippet']}
            """
            
            response = model.generate_content(prompt)
            summary = response.text
        except Exception as e:
            summary = "Error in AI generation or quota exceeded."
        
        item['AI Summary'] = summary
        summarized_data.append(item)
        
        # 更新進度條
        progress_bar.progress((index + 1) / total)
        
    return summarized_data

# --- 5. 按鈕與執行邏輯 ---
if st.button(t['btn_start'], type="primary"):
    if not api_key:
        st.error(t['error_api'])
    elif not user_keywords:
        st.error(t['error_no_key'])
    else:
        st.info(t['processing'])
        
        # 處理關鍵字
        keywords_list = user_keywords.split(",")
        
        # 1. 執行搜尋
        raw_news = search_news(keywords_list, ddg_time_param)
        
        if not raw_news:
            st.warning("No news found for the given keywords.")
        else:
            # 2. 執行 AI 摘要
            final_data = ai_summarize(raw_news, api_key, language_option)
            
            # 3. 轉為 DataFrame
            df = pd.DataFrame(final_data)
            
            # 整理欄位順序
            cols = ["Date", "Keyword", "Title", "AI Summary", "Source", "Link"]
            df = df[cols]
            
            st.success(t['success'])
            
            # 4. 顯示結果
            st.dataframe(df, use_container_width=True)
            
            # 5. Excel 下載
            # 修正：使用 ExcelWriter 確保編碼正確
            today_str = datetime.now().strftime("%Y%m%d")
            file_name = f"Foxconn_News_{today_str}.xlsx"
            
            # 將 DF 轉為 Excel Bytes
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
                
            st.download_button(
                label=t['download_btn'],
                data=buffer,
                file_name=file_name,
                mime="application/vnd.ms-excel"
            )
