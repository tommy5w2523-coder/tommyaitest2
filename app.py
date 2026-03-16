import streamlit as st
import google.generativeai as genai
import time
import os
import requests
from bs4 import BeautifulSoup

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
    3. 清除電視術語：自動刪除所有的畫面與過音提示（如 NS、OS、CG、Stand、Super 等）。同時，刪除文稿最末尾的記者署名與台呼（例如：TVBS新聞 OOO XXX 地點報導）。
    4. 處理受訪者口白：遇到「SB」或「BS」提示時，刪除該英文代號，並將受訪者職稱姓名與其口白內容，轉換為完整的對話格式：職稱姓名：「口白內容」。
    5. 通順文章結構（禁止超譯）：打破原本零碎的過音段落，用流暢的敘事邏輯把故事說完整。將口語化的文句潤飾為新聞報導文體，但「絕對不可超譯」或添加文稿中未提供的外部資訊。
    6. 插入 HTML 小標題：為內文進行邏輯分段，並在每個段落前加入字數介於 15 到 20 字 的小標題。小標題必須套用以下完整的 HTML 語法：
       <h2><span style="color:#0000FF;">小標題文字</span></h2>
    7. 預擬 6 個專屬圖說：根據內文情境，在文章最下方產出 6 句供挑選的圖說。每一句圖說的前後與版權標示，必須嚴格套用以下語法：
       <br /> 圖說內容文字。（圖／TVBS） <br />
       【圖說特別規範】：直接輸出句子即可，**絕對禁止**在句子前面加上「圖說：」、「圖說1：」等任何提示或註記字眼。
    8. 強制純文字與程式碼區塊輸出：為了防止發稿系統的介面隱藏或吃掉 HTML 語法，轉換後的「所有成品內容」（包含內文、小標題、圖說），必須全部包裝在一個 `text` 的程式碼區塊中輸出（即 ```text ... ```），確保原始碼一字不漏地呈現。

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
    
    # 【優化 1】將單行輸入改為可自由發揮的大文字框
    custom_instructions = st.text_area(
        "💡 採訪背景與特殊指令 (選填)：", 
        height=100, 
        placeholder="請直接用白話文告訴 AI 狀況。例如：\n1. 這是關於美股與核能產業的專訪。\n2. 音檔中的女聲是A，男聲是B。\n3. 遇到Constellation Energy請翻成星座能源。"
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
                            【聽打特別規範】：請自動過濾無意義的語助詞（如：喔、啊、呃、那個、對對對）、結巴或重複字詞。若遇到收音不清、長時間空白或背景雜音，請直接略過，絕對禁止無限重複同一個字或詞。

                            1. 【中文逐字稿】：產出高準確度且語句通順的中文逐字稿。
                               - 語者辨識：請務必分辨不同的說話者。
                               - 排版分段：只要「換人說話」，或是「同一人發言內容過長（超過 3 到 4 句）」，請務必「換行分段」呈現，絕對不要把所有文字濃縮擠成一大塊。
                            """
                        else:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞。若遇到收音不清請略過。

                            1. 【雙語比對逐字稿】：自動辨識音檔中的原始語言，產出精確的「原文逐字稿」。
                               - 語者辨識：請務必分辨不同的說話者。
                               - 排版分段：只要換人說話就必須換行。在每一個原文段落的正下方，請直接提供對應的「中文翻譯」。不同語者的發言區塊之間，請務必「空一行」隔開。
                            """
                    else:
                        if "1." in task_option:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下三項任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞、結巴或重複字詞。若遇到收音不清請略過。

                            1. 【中文逐字稿】：產出高準確度且語句通順的中文逐字稿。
                               - 語者辨識：請務必分辨不同的說話者。
                               - 排版分段：只要「換人說話」，或「同一人發言超過 3 到 4 句」，請務必「換行分段」呈現。
                            2. 【重點條列】：根據逐字稿內容，精煉並條列出核心重點。
                            3. 【電視新聞標題】：根據音檔核心內容，生成 3 個具備「電視新聞感」的標題（15-17字內，全形空白斷句，不加句號）。
                            """
                        else:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下三項任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞、結巴或重複字詞。若遇到收音不清請略過。

                            1. 【雙語比對逐字稿】：產出精確的「原文逐字稿」。
                               - 語者辨識：請務必分辨不同的說話者。
                               - 排版分段：換人說話必須換行。在每一個原文段落的正下方，請直接提供對應的「中文翻譯」。區塊之間請空一行。
                            2. 【中文重點條列】：總結音檔內容，條列出中文核心重點。
                            3. 【電視新聞標題】：生成 3 個具備「電視新聞感」的中文標題（15-17字內，全形空白斷句，不加句號）。
                            """
                    
                    prompt_text += """
                    【語境校正強制指令】：你具備台灣時事、政治與財經常識。請務必根據上下文的邏輯，自動校正同音錯字。絕對不允許出現不合邏輯的同音異字。
                    """
                    
                    # 【優化 2】將白話文指令轉換為最高霸王條款
                    if custom_instructions:
                        prompt_text += f"""
                        \n=========================================
                        【記者補充背景與最高指令】：
                        {custom_instructions}
                        =========================================
                        請將上述記者的補充資訊作為「最高指導原則」：
                        1. 若其中有指定說話者的身分（例如提示男聲/女聲是誰、或者主角是誰），請在產出逐字稿時「直接使用這些具體的名稱」來標註說話者，絕對不要再使用通用的「受訪者A」或「記者」。
                        2. 若其中有提供專有名詞或背景知識，請據此精準理解語境並校正相關字眼。
                        """
                    
# 微調物理限制器：放寬頻率懲罰，加入存在懲罰 (鼓勵往下聽新內容)
                    safe_config = genai.GenerationConfig(
                        temperature=0.2, 
                        frequency_penalty=0.5, 
                        presence_penalty=0.5
                    )
                    
                    response = model.generate_content([audio_file, prompt_text], generation_config=safe_config)
                    
                    # 加上「防交白卷」安全氣囊
                    if not response.candidates or not response.candidates[0].content.parts:
                        st.error("⚠️ AI 這次交了白卷！可能是該段音檔雜音過多、全為空白，或是 AI 觸發了防護機制。請確認音檔內容或稍微剪輯後再試一次。")
                    else:
                        st.markdown("### 📝 聽打結果：")
                        st.code(response.text, language="markdown")
                 
                    
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
