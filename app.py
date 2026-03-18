import streamlit as st
import google.generativeai as genai
import time
import os
import requests
from bs4 import BeautifulSoup
import urllib3

# 關閉 urllib3 的安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 網頁基礎設定與介面美化 ====================
st.set_page_config(page_title="新聞 AI 工作台", page_icon="📺")

hide_streamlit_style = """
            <style>
            [data-testid="stToolbar"] {visibility: hidden !important;}
            #MainMenu {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            header {visibility: hidden !important;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

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
tab1, tab2, tab3, tab4, tab5 = st.tabs([" SOT改寫", " 語音轉逐字", " 網頁重點擷取", " 快速生成稿標", " 新聞稿改寫"])

# ==================== 分頁 1：改寫文章與網頁格式 ====================
with tab1:
    st.header("稿件處理與格式化")
    
    system_prompt = """
    # Role
    你是一位專業且高效的「電視新聞轉網路新聞格式轉換員」，專門處理高節奏的電視台新聞發稿作業。你的任務是接收一段電視新聞文稿（包含主播稿頭、過音OS、受訪者Bite、畫面指示、台呼等），並嚴格依照指定規範，將其轉換為流暢、排版精確且帶有指定 HTML 標籤的網路新聞文稿。

    # Core Rules (嚴格執行)
    1. 保留稿頭：文稿的第一段必須「一字不漏」完全保留。
    2. 精煉標題：產出 25 到 30 字的大標題。強制加「影音／」前綴，全形空白斷句，不加句號。
    3. 清除電視術語：刪除畫面與過音提示（NS、OS、CG等）及末尾署名台呼。
    4. 處理受訪者口白：轉換為完整的對話格式：職稱姓名：「口白內容」。
    5. 通順文章結構：打破零碎過音段落，用流暢敘事邏輯把故事說完整。
    6. 插入 HTML 小標題：在段落前加入 15 到 20 字的小標題。必須套用 <h2><span style="color:#0000FF;">小標題</span></h2> 語法。
    7. 預擬 6 個專屬圖說：產出 6 句圖說。必須套用 <br /> 圖說。（圖／TVBS） <br /> 語法。
    8. 強制純文字與程式碼區塊輸出：所有內容必須包裝在 text 程式碼區塊中輸出。
    """    
    user_text = st.text_area("請貼上SOT文稿：", height=200)
    
    if st.button("🚀 開始改寫與排版"):
        if user_text:
            with st.spinner('AI 正在幫你改寫與排版中...'):
                try:
                    model = genai.GenerativeModel(selected_model_name)
                    response = model.generate_content(system_prompt + "\n\n以下是原始稿件：\n" + user_text)
                    st.markdown("### ✨ 處理結果 (可直接複製貼上後台)：")
                    st.code(response.text, language="markdown")
                except Exception as e:
                    st.error(f"生成失敗，錯誤原因：{e}")

# ==================== 分頁 2：逐字稿與翻譯 ====================
with tab2:
    st.header("多媒體逐字稿生成")
    
    uploaded_file = st.file_uploader("請上傳音檔或影片檔 (支援 mp3, mp4, wav, m4a, mov 等)", type=['mp3', 'mp4', 'wav', 'm4a', 'mov'])
    st.info("💡 **手機版上傳戰術提示**：iPhone 語音備忘錄請先「儲存到檔案」再上傳！")
    
    task_option = st.radio("你想做什麼？", ["1. 產生中文逐字稿，並條列重點與 3 個重點標題", "2. 產生原文逐字稿與中文翻譯比對，並生成 3 個重點標題"])
    fast_mode = st.checkbox("⚡ 快速聽打（無重點整理與標題）")
    custom_instructions = st.text_area("💡 採訪背景與特殊指令 (選填)：", height=100)
    
    if st.button("🎧 開始聽打分析"):
        if uploaded_file:
            with st.spinner('上傳與處理中，這可能需要幾分鐘...'):
                try:
                    temp_file_path = uploaded_file.name
                    with open(temp_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    st.toast("檔案上傳中，請稍候...")
                    audio_file = genai.upload_file(path=temp_file_path)
                    
                    while audio_file.state.name == "PROCESSING":
                        time.sleep(2)
                        audio_file = genai.get_file(audio_file.name)
                        
                    if audio_file.state.name == "FAILED":
                        st.error("Google 伺服器解析檔案失敗。")
                        st.stop()
                    
                    st.toast("檔案解析完成！AI 開始聽打中...")
                    model = genai.GenerativeModel(selected_model_name)
                    
                    if fast_mode:
                        prompt_text = "請聆聽音檔產出精確逐字稿。自動過濾語助詞，收音不清請略過。換人說話請換行。"
                    else:
                        prompt_text = "請聆聽音檔產出精確逐字稿。過濾語助詞。換人說話請換行。最後附上重點整理與3個電視新聞標題。"
                    
                    prompt_text += "\n【語境校正強制指令】：具備台灣時事與政經常識，自動校正同音錯字。"
                    if custom_instructions:
                        prompt_text += f"\n【最高指導原則】：{custom_instructions}"
                    
                    safe_config = genai.GenerationConfig(temperature=0.2)
                    custom_safety_settings = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ]
                    
                    response = model.generate_content([audio_file, prompt_text], generation_config=safe_config, safety_settings=custom_safety_settings)
                    
                    if not response.candidates or not response.candidates[0].content.parts:
                        st.error("⚠️ AI 這次交了白卷！可能是雜音過多或觸發防護機制。")
                    else:
                        st.markdown("### 📝 聽打結果：")
                        st.code(response.text, language="markdown")
                    
                    os.remove(temp_file_path)
                    genai.delete_file(audio_file.name)
                except Exception as e:
                    st.error(f"生成失敗：{e}")

# ==================== 分頁 3：網頁重點擷取 ====================
with tab3:
    st.header("多網頁重點擷取與編譯")
    
    target_urls_input = st.text_area("請貼上文章網址 (URL)，若有多個網址請「換行」貼上：", height=150)
    
    if st.button("⚡ 擷取並分析重點"):
        urls = [url.strip() for url in target_urls_input.split('\n') if url.strip()]
        if not urls:
            st.warning("請先輸入至少一個網址喔！")
        else:
            with st.spinner('爬取網頁內容中...'):
                combined_article_text = ""
                success_count = 0
                for i, url in enumerate(urls):
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        response = requests.get(url, headers=headers, timeout=10, verify=False)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        paragraphs = soup.find_all('p')
                        article_text = "\n".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 10])
                        if article_text:
                            combined_article_text += f"==== 【網站 {i+1}】 ====\n{article_text}\n\n"
                            success_count += 1
                    except Exception as e:
                        st.error(f"❌ 網站 {i+1} 連線失敗：{e}")
                
                if success_count > 0:
                    try:
                        model = genai.GenerativeModel(selected_model_name)
                        prompt_text = f"你是一位資深國際新聞編譯。請整理以下多篇網頁內容的大綱與人物說法。外文請自動翻譯成中文。\n\n{combined_article_text}"
                        response = model.generate_content(prompt_text)
                        st.success("分析完成！")
                        st.code(response.text, language="markdown")
                    except Exception as e:
                        st.error(f"生成失敗：{e}")

# ==================== 分頁 4：主播稿頭與電視標題生成 ====================
with tab4:
    st.header(" 快速生成稿頭與標題")
    
    raw_news_text = st.text_area("請貼上你寫好的新聞內文：", height=200)
    
    if st.button("📺 產出稿頭與標題"):
        if not raw_news_text:
            st.warning("請先貼上新聞內文喔！")
        else:
            with st.spinner('編輯台長官審稿中...'):
                try:
                    model = genai.GenerativeModel(selected_model_name)
                    prompt_text = f"""
                    你是一位台灣電視新聞台的核稿編輯。請依據以下新聞內文，執行兩項任務：
                    1. 【撰寫主播稿頭】：濃縮最核心精華，寫成主播引言。限制在 100 字內。所有標點符號僅限使用「半形」。請 100% 貼合原文客觀事實。
                    2. 【下 3 個電視新聞大標題】：每個標題字數介於 17 到 20 個字。僅使用「半形空白」斷句，每個標題【只能有一次空白】。無句號逗號。至少 1 個標題需引用金句，金句放後半段。引述格式使用「人物:」格式。
                    原始文稿：\n{raw_news_text}
                    """
                    safe_config = genai.GenerationConfig(temperature=0.1)
                    response = model.generate_content(prompt_text, generation_config=safe_config)
                    st.success("產出完成！")
                    st.code(response.text, language="markdown")
                except Exception as e:
                    st.error(f"生成失敗：{e}")

# ==================== 分頁 5：新聞稿轉換 (記憶體 + 一鍵複製 + 專業稱謂版) ====================
with tab5:
    st.header("新聞稿改寫")
    st.markdown("貼上官方聲明/公關稿，AI 將自動轉換成口語化、客觀且好讀的網路新聞報導。")
    
    # 記憶體初始化 (確保不會失憶)
    if "tab5_generated_news" not in st.session_state:
        st.session_state.tab5_generated_news = ""
    
    pr_text = st.text_area("請貼上官方聲明或公關稿內文：", height=200, placeholder="將長篇大論的聲明稿貼在這裡...")
    pr_context = st.text_input("💡 補充背景 (選填)：", placeholder="幫助 AI 掌握前因後果...")
    
    if st.button("🚀 產出網路新聞"):
        if not pr_text:
            st.warning("請先貼上聲明或公關稿喔！")
        else:
            with st.spinner('改寫中...'):
                try:
                    model = genai.GenerativeModel(selected_model_name)
                    
                    # 💡 提示詞升級：加入第 3 點「人物稱謂鐵律」
                    prompt_text = f"""
                    你現在是一位台灣知名電視台所屬新聞網站的「資深網路新聞編輯」。
                    任務：將官方聲明改寫為客觀、流暢、口語化且易讀的【網路新聞報導】。
                    
                    請嚴格遵守以下改寫鐵律：
                    1. 【口語化與禁止超譯】：必須要用口語化、自然流暢的新聞敘事方式改寫。【絕對禁止超譯或腦補】，必須 100% 貼合原始聲明。
                    2. 【視角強制轉換】：第一人稱（如：本公司、本人），強制轉換為第三人稱（如：該公司、某某某表示）。
                    3. 【人物稱謂鐵律（平面新聞規範）】：同一人物在新聞稿中第一次出現時，請寫出「完整職稱＋姓名」（例如：行政院副院長鄭麗君）。後續段落若再次提及同一人，【請一律只寫姓名】（例如：鄭麗君），絕對禁止重複加上職稱或類似「鄭副院長」的稱呼。
                    4. 【去除公關水份】：刪除過度吹捧詞彙，保留核心事實。
                    5. 【吸睛大標題】：撰寫 1 個大標題（25字內，全形空白斷句，無句號）。【注意：請直接產出內文，絕對不要生成任何段落小標題】。
                    6. 【新聞導言】：第一段必須包含 5W1H，100 字以內交代輪廓。
                    7. 【保留核心金句】：從聲明稿中萃取一兩句金句，以引號（「」）原音重現。
                    
                    記者補充背景：{pr_context}
                    原始聲明：\n{pr_text}
                    """
                    
                    safe_config = genai.GenerationConfig(temperature=0.2)
                    response = model.generate_content(prompt_text, generation_config=safe_config)
                    
                    # 將產生的內容存進記憶體
                    st.session_state.tab5_generated_news = response.text
                        
                except Exception as e:
                    st.error(f"生成失敗，錯誤原因：{e}")

    # 顯示區塊 (編輯框 + 同步一鍵複製框)
    if st.session_state.tab5_generated_news:
        st.success("網編改寫完成！")
        
        # 上方：讓記者可以手動微調的編輯框
        edited_text = st.text_area(
            "📝 第一步：在此框內閱讀、上下捲動，並可直接打字修改", 
            value=st.session_state.tab5_generated_news, 
            height=400
        )
        
        # 同步更新記憶體 (只要有打字修改，就存起來給下方的複製框用)
        if edited_text != st.session_state.tab5_generated_news:
            st.session_state.tab5_generated_news = edited_text
        
        # 下方：負責提供「一鍵複製」按鈕的唯讀區塊
        st.markdown("📋 第二步：確認修改完畢後，點擊下方區塊**「右上角的複製圖示」**即可一鍵帶走👇")
        st.code(st.session_state.tab5_generated_news, language="markdown")
