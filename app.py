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

# --- 注入 CSS 隱形藥水：打造專業封閉系統質感 ---
hide_streamlit_style = """
            <style>
            /* 隱藏右上角的 GitHub 圖示、Deploy 按鈕與預設 Toolbar */
            [data-testid="stToolbar"] {visibility: hidden !important;}
            /* 隱藏右上角的漢堡主選單 (三個點) */
            #MainMenu {visibility: hidden !important;}
            /* 隱藏最底部的 Made with Streamlit 浮水印 */
            footer {visibility: hidden !important;}
            /* 隱藏最上方的預設彩色裝飾線 */
            header {visibility: hidden !important;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# ---------------------------------------------

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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 新聞稿改寫", "🎧 多媒體逐字稿", "🔗 網頁重點擷取", "💡 稿頭與標題生成", "📰 新聞稿轉換"])

# ==================== 分頁 1：改寫文章與網頁格式 ====================
with tab1:
    st.header("稿件處理與格式化")
    
    system_prompt = """
    # Role
    你是一位專業且高效的「電視新聞轉網路新聞格式轉換員」，專門處理高節奏的電視台新聞發稿作業。你的任務是接收一段電視新聞文稿（包含主播稿頭、過音OS、受訪者Bite、畫面指示、台呼等），並嚴格依照指定規範，將其轉換為流暢、排版精確且帶有指定 HTML 標籤的網路新聞文稿。

    # Core Rules (嚴格執行)
    1. 保留稿頭：文稿的第一段（通常為主播稿頭）必須「一字不漏」完全保留，包含其原有的標點符號。
    2. 精煉標題：忽略文稿中的佔位符號。請綜合內文，產出一個字數介於 25 到 30 字 的大標題。
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

    [第一個 HTML 小標題]
    [轉換後的第一段內文]

    [第二個 HTML 小標題]
    [轉換後的第二段內文]

    [圖說1，含前後 HTML 標籤]
    [圖說2，含前後 HTML 標籤]
    [圖說3，含前後 HTML 標籤]
    [圖說4，含前後 HTML 標籤]
    [圖說5，含前後 HTML 標籤]
    [圖說6，含前後 HTML 標籤]
    """    
    user_text = st.text_area("請貼上原始採訪稿或雜亂的筆記：", height=200)
    
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
    st.info("💡 **手機版上傳戰術提示**：如果是 iPhone「語音備忘錄」的錄音，請先在備忘錄點擊「分享」➔「儲存到檔案」，接著再從下方點擊上傳喔！")
    
    task_option = st.radio("你想做什麼？", [
        "1. 產生中文逐字稿，並條列重點與 3 個重點標題",
        "2. 產生原文逐字稿與中文翻譯比對，並生成 3 個重點標題"
    ])
    
    fast_mode = st.checkbox("⚡ 啟動極速聽打模式（⚠️ 注意：無重點整理 + 無新聞標題，只直出純逐字稿，適合搶快！）")
    
    custom_instructions = st.text_area(
        "💡 採訪背景與特殊指令 (選填)：", 
        height=100, 
        placeholder="請直接用白話文告訴 AI 狀況。例如：\n1. 這是一篇關於美股與核能產業的專訪。\n2. 音檔中的女聲是記者，男聲是分析師黃國昌。\n3. 遇到雜音請略過，絕對不要跳針猜測。"
    )
    
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
                        st.error("Google 伺服器解析檔案失敗，請確認檔案格式是否損毀。")
                        st.stop()
                    
                    st.toast("檔案解析完成！AI 開始聽打中...")
                    model = genai.GenerativeModel(selected_model_name)
                    
                    if fast_mode:
                        if "1." in task_option:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞。若遇到收音不清請直接略過，絕對禁止猜測或重複上一句話。

                            1. 【中文逐字稿】：產出高準確度且語句通順的中文逐字稿。
                               - 語者辨識：請務必分辨不同的說話者。
                               - 排版分段：只要「換人說話」，或是「同一人發言內容過長」，請務必「換行分段」呈現。
                            """
                        else:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞。若遇到收音不清請直接略過。

                            1. 【雙語比對逐字稿】：自動辨識音檔中的原始語言，產出精確的「原文逐字稿」。
                               - 排版分段：換人說話必須換行。在每一個原文段落的正下方，直接提供對應的「中文翻譯」。區塊之間請空一行。
                            """
                    else:
                        if "1." in task_option:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下三項任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞。若遇到收音不清請直接略過。

                            1. 【中文逐字稿】：產出高準確度且語句通順的中文逐字稿。
                               - 語者辨識：請務必分辨不同的說話者。
                               - 排版分段：換人說話或發言過長，請務必換行分段。
                            2. 【重點條列】：根據逐字稿內容，精煉並條列出核心重點。
                            3. 【電視新聞標題】：生成 3 個具備「電視新聞感」的標題（15-17字內，全形空白斷句，不加句號）。
                            """
                        else:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下三項任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞。若遇到收音不清請直接略過。

                            1. 【雙語比對逐字稿】：產出精確的「原文逐字稿」。
                               - 排版分段：換人說話必須換行。在原文段落正下方，直接提供對應的「中文翻譯」。
                            2. 【中文重點條列】：總結音檔內容，條列出中文核心重點。
                            3. 【電視新聞標題】：生成 3 個具備「電視新聞感」的中文標題（15-17字內，全形空白斷句，不加句號）。
                            """
                    
                    prompt_text += """
                    【語境校正強制指令】：你具備台灣時事、政治、財經與國際常識。請務必根據上下文的邏輯，自動校正同音錯字。絕對不允許出現不合邏輯的同音異字。
                    """
                    
                    if custom_instructions:
                        prompt_text += f"""
                        \n=========================================
                        【記者補充背景與最高指令】：
                        {custom_instructions}
                        =========================================
                        請將上述記者的補充資訊作為「最高指導原則」，若有指定說話者的身分，請在逐字稿中直接使用該名稱標註。
                        """
                    
                    safe_config = genai.GenerationConfig(temperature=0.2)
                    
                    # 🛡️ 解除 Google 預設的道德與安全限制，防止新聞敏感詞被擋
                    custom_safety_settings = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ]
                    
                    response = model.generate_content(
                        [audio_file, prompt_text], 
                        generation_config=safe_config,
                        safety_settings=custom_safety_settings
                    )
                    
                    if not response.candidates or not response.candidates[0].content.parts:
                        st.error("⚠️ AI 這次交了白卷！可能是該段音檔雜音過多、全為空白，或是 AI 觸發了防護機制。請確認音檔內容或稍微剪輯後再試一次。")
                    else:
                        st.markdown("### 📝 聽打結果：")
                        st.code(response.text, language="markdown")
                    
                    os.remove(temp_file_path)
                    genai.delete_file(audio_file.name)
                    
                except Exception as e:
                    st.error(f"生成失敗，錯誤原因：{e}")

# ==================== 分頁 3：網頁重點擷取 ====================
with tab3:
    st.header("🔗 多重網頁重點擷取與編譯")
    st.markdown("可同時貼上多個國內外新聞網址，AI 將自動判斷語言、翻譯外文，並為你整理大綱與人物說法。")
    
    target_urls_input = st.text_area("請貼上文章網址 (URL)，若有多個網址請「換行」貼上：", height=150, placeholder="https://網址1.com\nhttps://網址2.com")
    
    if st.button("⚡ 擷取並分析重點"):
        urls = [url.strip() for url in target_urls_input.split('\n') if url.strip()]
        
        if not urls:
            st.warning("請先輸入至少一個網址喔！")
        else:
            with st.spinner('偵察兵連線中，正在依序爬取網頁內容...'):
                combined_article_text = ""
                success_count = 0
                
                for i, url in enumerate(urls):
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                        response = requests.get(url, headers=headers, timeout=10, verify=False)
                        response.raise_for_status() 
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        paragraphs = soup.find_all('p')
                        article_text = "\n".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 10])
                        
                        if article_text:
                            combined_article_text += f"==== 【網站 {i+1}】來源網址：{url} ====\n{article_text}\n\n"
                            success_count += 1
                        else:
                            st.warning(f"⚠️ 網站 {i+1} ({url}) 抓不到內文，可能遭遇反爬蟲機制，已略過。")
                    except Exception as e:
                        st.error(f"❌ 網站 {i+1} ({url}) 連線或爬取失敗：{e}")
                
                if success_count == 0:
                    st.error("所有網址都無法成功抓取內文，請確認網址是否正確。")
                    st.stop()
                    
                st.toast(f"✅ 成功抓取 {success_count} 個網頁！交給 AI 處理中...")
                
                try:
                    model = genai.GenerativeModel(selected_model_name)
                    
                    prompt_text = f"""
                    你現在是一位資深的電視新聞國際中心編譯與編輯。
                    我會給你 {success_count} 篇從網路上擷取下來的文章內文，請針對每一個網站的內容「分別」進行處理。
                    
                    【處理規則】：請自動偵測各網站原文的語言，並依照以下兩種狀況嚴格執行。
                    
                    狀況 A：如果原文是「中文」
                    1. 【文章大綱】：精煉整理出該篇文章的核心大綱。
                    2. 【人物說法】：若內文有提及任何人物的發言、聲明或受訪內容，請條列式整理出來（請務必標明說話者是誰；若無人物發言則寫「無」）。
                    
                    狀況 B：如果原文是「外文」（包含英文、日文、韓文等任何非中文語言）
                    1. 【全文明快翻譯】：請務必「先」將整篇文章翻譯成流暢、符合台灣新聞語感的中文。
                    2. 【文章大綱】：根據翻譯後的內容，精煉整理出核心大綱。
                    3. 【人物說法】：若內文有提及任何人物的發言、聲明或受訪內容，請條列式提取出來（請標明說話者是誰，並提供流暢的中文翻譯；若無則寫「無」）。

                    【排版與區隔要求】：
                    請務必明確區隔不同網站的內容。請使用「📺 【網站 1】分析」、「📺 【網站 2】分析」做為大標題。絕對不能將不同網站的資訊混淆在一起，讓編輯能一目了然。

                    以下是爬取到的多篇文章內文：
                    ---
                    {combined_article_text}
                    """
                    
                    response = model.generate_content(prompt_text)
                    
                    st.success("編譯與分析完成！")
                    st.markdown("### 📊 多重網頁重點結果：")
                    st.code(response.text, language="markdown")
                    
                    with st.expander("👀 點我查看 AI 爬抓到的「原始網頁純文字」"):
                        st.text(combined_article_text)
                        
                except Exception as e:
                    st.error(f"生成失敗，錯誤原因：{e}")

# ==================== 分頁 4：主播稿頭與電視標題生成 ====================
with tab4:
    st.header("💡 主播稿頭與電視標題生成")
    st.markdown("貼上寫好的內文，AI 瞬間幫你濃縮出 100 字內的主播稿頭，並產出符合台灣新聞台鏡面邏輯的 3 個精準大標。")
    
    raw_news_text = st.text_area("請貼上你寫好的新聞內文：", height=200, placeholder="將採訪整理好的內文貼在這裡...")
    
    if st.button("📺 產出稿頭與標題"):
        if not raw_news_text:
            st.warning("請先貼上新聞內文喔！")
        else:
            with st.spinner('編輯台長官審稿中...正在生標題與稿頭...'):
                try:
                    model = genai.GenerativeModel(selected_model_name)
                    
                    prompt_text = f"""
                    你是一位台灣電視新聞台的核稿編輯。請依據以下新聞內文，執行兩項任務：

                    1. 【撰寫主播稿頭（Lead）】：
                       - 任務：濃縮最核心精華，寫成主播引言。
                       - 限制：長度控制在 100 個字以內。
                       - 格式：所有標點符號僅限使用「半形符號」（如半形逗號,、句號.）。
                       - 語氣：請 100% 貼合原文客觀事實，使用平實中立的新聞語氣，只陳述已發生的事與具體對話。

                    2. 【下 3 個電視新聞大標題（CG Headline）】：
                       - 任務：抓出新聞重點或受訪者金句，客觀呈現事實。
                       - 限制：每個標題字數介於 17 到 20 個字之間。
                       - 斷句與標點：僅使用「半形空白」來斷句，每個標題【只能有一次空白】。結尾或中間皆不使用句號與逗號。若需增添語氣可使用半形的「!」或「?」。
                       - 排版鐵律：3 個標題中，至少要有 1 個標題引用核心受訪者的回答，且金句必須放在標題的【後半段】（半形空白之後）。
                       - 引述格式：使用「人物:」格式（半形冒號）。同一個標題中，人物的「稱謂」與「姓名」請擇一精簡呈現（例如：改為「黃國昌:」或「立委:」）。

                    原始文稿：
                    ---
                    {raw_news_text}
                    """
                    
                    safe_config = genai.GenerationConfig(temperature=0.1)
                    response = model.generate_content(prompt_text, generation_config=safe_config)
                    
                    st.success("產出完成！")
                    st.markdown("### 📝 稿頭與標題結果：")
                    st.code(response.text, language="markdown")
                        
                except Exception as e:
                    st.error(f"生成失敗，錯誤原因：{e}")

# ==================== 分頁 5：新聞稿轉換 ====================
with tab5:
    st.header("📰 新聞稿轉換")
    st.markdown("貼上政府機關、政治人物或企業的官方聲明/公關稿，AI 將自動去除「公關贅字」，轉換成口語化、客觀且好讀的網路新聞報導。")
    
    pr_text = st.text_area("請貼上官方聲明或公關稿內文：", height=200, placeholder="將長篇大論的聲明稿、臉書貼文貼在這裡...")
    pr_context = st.text_input("💡 補充背景 (選填)：", placeholder="例如：這是針對早上黃國昌記者會的回應，幫助 AI 掌握前因後果...")
    
    if st.button("🚀 產出網路新聞"):
        if not pr_text:
            st.warning("請先貼上聲明或公關稿喔！")
        else:
            with st.spinner('資深網編改寫中...'):
                try:
                    model = genai.GenerativeModel(selected_model_name)
                    
                    prompt_text = f"""
                    你現在是一位台灣知名電視台所屬新聞網站的「資深網路新聞編輯」。
                    你的任務是將一篇【官方聲明】、【公關稿】或【政治人物社群貼文】，改寫為客觀、流暢、口語化且易讀的【網路新聞報導】。

                    請嚴格遵守以下改寫鐵律：
                    1. 【口語化與禁止超譯】：文章必須要用口語化、自然流暢的新聞敘事方式改寫，不再死板板。但【絕對禁止超譯或腦補】，必須 100% 貼合原始聲明的事實，不可自行延伸推論或加入原文未提及的資訊。
                    2. 【視角強制轉換】：將官方聲明的第一人稱（如：本公司、本黨、我方、本人），強制轉換為第三人稱的新聞客觀視角（如：該公司、該黨、某某某表示）。
                    3. 【去除公關水份】：刪除過度吹捧、情緒化或無實質意義的公關詞彙，保留核心事實與重點。若有專有名詞請維持精確。
                    4. 【吸睛大標題】：撰寫 1 個符合網路新聞胃口的大標題（字數 25 字以內，具備資訊量與吸引力，使用「全形空白」斷句，不加句號）。【注意：請直接產出內文，絕對不要生成任何段落小標題】。
                    5. 【新聞導言（Lead）】：第一段必須是包含 5W1H 的標準新聞導言，用 100 字以內交代整起事件的輪廓與最新進度。
                    6. 【保留核心金句】：從聲明稿中萃取最具代表性的一到兩句話，以引號（「」）作為原音重現，增加報導可信度。

                    記者補充背景資訊（若無則忽略，若有請融入導言中交代脈絡）：
                    {pr_context}

                    以下是原始聲明/公關稿：
                    ---
                    {pr_text}
                    """
                    
                    # 維持 0.2 微溫，讓它有能力潤飾語氣，但又不敢隨便亂編事實
                    safe_config = genai.GenerationConfig(temperature=0.2)
                    response = model.generate_content(prompt_text, generation_config=safe_config)
                    
                    st.success("網編改寫完成！")
                    st.markdown("### 📰 網路新聞成品：")
                    # 改用 text_area，不僅會自動換行、可上下捲動，還能直接在裡面編輯微調！
                    st.text_area("✅ 可直接上下捲動閱讀、全選複製，或在框內修改文字：", value=response.text, height=400)
                        
                except Exception as e:
                    st.error(f"生成失敗，錯誤原因：{e}")
