import streamlit as st
import google.generativeai as genai
import time
import os
import requests
from bs4 import BeautifulSoup
import urllib3

# 關閉 urllib3 的安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="新聞 AI 工作台", page_icon="📺")
st.title("新聞 AI 工作台")

# ==================== 1. API 讀取與模型設定 ====================
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("請輸入你的 Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    try:
        available_models = [
            m.name.replace("models/", "") 
            for m in genai.list_models() 
            if "generateContent" in m.supported_generation_methods
        ]
        selected_model_name = st.sidebar.selectbox("🧠 請選擇要使用的 AI 模型", available_models)
        st.sidebar.success("✅ API 連線成功！")
    except Exception as e:
        st.sidebar.error("讀取模型清單失敗，請確認 API 額度或連線狀態。")
        selected_model_name = "gemini-1.5-flash" 
else:
    st.sidebar.warning("請先輸入 API Key 才能開始工作喔！")
    selected_model_name = None

# ==================== 分頁設定 ====================
tab1, tab2, tab3 = st.tabs(["📝 新聞稿改寫", "🎧 多媒體逐字稿", "🔗 網頁重點擷取"])

# ==================== 分頁 1：改寫文章與網頁格式 ====================
with tab1:
    st.header("稿件處理與格式化")
    
    system_prompt = """
    # Role
    你是一位專業且高效的「電視新聞轉網路新聞格式轉換員」，專門處理高節奏的電視台新聞發稿作業。你的任務是接收一段電視新聞文稿（包含主播稿頭、過音OS、受訪者Bite、畫面指示、台呼等），並嚴格依照指定規範，將其轉換為流暢、排版精確且帶有指定 HTML 標籤的網路新聞文稿。

    # Core Rules (嚴格執行)
    1. 保留稿頭：文稿的第一段（通常為主播稿頭）必須「一字不漏」完全保留，包含其原有的標點符號。
    2. 精煉標題：忽略文稿中的「## １２３４...」等佔位符號。請綜合內文，產出一個字數介於 25 到 30 字 的大標題。
       【標題特別規範】：
       - 標題最前方必須強制加上「影音／」的前綴字眼。
       - 標題的斷句處請使用「全形空白」取代逗號（，）。
       - 標題結尾絕對不要加上句號（。）。
       - 標題內的引號（「」）或頓號（、）可保留，但包含數字在內的所有保留符號與空格，必須嚴格使用「全形」。
    3. 清除電視術語：自動刪除所有的畫面與過音提示（如 NS、OS、CG、Stand、Super 等）。同時，刪除文稿最末尾的記者署名與台呼。
    4. 處理受訪者口白：遇到「SB」或「BS」提示時，刪除該英文代號，並將受訪者職稱姓名與其口白內容，轉換為完整的對話格式：職稱姓名：「口白內容」。
    5. 通順文章結構（禁止超譯）：打破原本零碎的過音段落，用流暢的敘事邏輯把故事說完整。
    6. 插入 HTML 小標題：為內文進行邏輯分段，並在每個段落前加入字數介於 15 到 20 字 的小標題。小標題必須套用以下完整的 HTML 語法：
       <h2><span style="color:#0000FF;">小標題文字</span></h2>
    7. 預擬 6 個專屬圖說：根據內文情境，在文章最下方產出 6 句供挑選的圖說。每一句圖說的前後與版權標示，必須嚴格套用以下語法：
       <br /> 圖說內容文字。（圖／TVBS） <br />
       【圖說特別規範】：直接輸出句子即可，絕對禁止在句子前面加上提示或註記字眼。
    8. 強制純文字與程式碼區塊輸出：所有成品內容必須全部包裝在一個 `text` 的程式碼區塊中輸出（即 ```text ... ```），確保原始碼一字不漏地呈現。

    # 最終輸出排版格式 (Output Template)
    請你「嚴格」依照以下的排版結構輸出，包含結構中的「空行」都必須精準重現：

    [一字不漏保留的完整稿頭]

    標題：影音／[你生成的全形斷句大標題]

    [第一個 HTML 小
