import streamlit as st
import google.generativeai as genai
import os
import time

# 網頁基本設定
st.set_page_config(page_title="AI 新聞工作台", page_icon="🤖", layout="wide")
st.title("專屬 AI 新聞工作台 🎙️✍️")

# 嘗試從 Streamlit 雲端保險箱讀取 API Key
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    # 如果保險箱沒有（例如你在本地端測試），才顯示側邊欄輸入框
    api_key = st.sidebar.text_input("請輸入你的 Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    # 抓取模型清單
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name.replace('models/', ''))
        
        selected_model_name = st.sidebar.selectbox(
    "🧠 請選擇要使用的 AI 模型", 
    [
        "gemini-2.5-flash", 
        "gemini-2.0-flash", 
        "gemini-1.5-flash", 
        "gemini-1.5-pro"
    ]
)
        st.sidebar.success(f"連線成功！目前使用：{selected_model_name}")
        
    except Exception as e:
        st.error(f"讀取模型列表失敗，請確認 API Key 是否正確。錯誤訊息：{e}")
        st.stop()
        
else:
    st.warning("👈 請先在左側輸入你的 API Key 才能開始使用喔！")
    st.stop()

# 建立兩個分頁區塊
tab1, tab2 = st.tabs(["📝 新聞稿與 CG 自動排版", "🎧 音軌/影片逐字稿聽打"])

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
                    st.markdown(response.text)
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
    
    # 更人性化、提示更明確的開關
    fast_mode = st.checkbox("⚡ 啟動極速聽打模式（⚠️ 注意：無重點整理 + 無新聞標題，只直出純逐字稿，適合搶快！）")
    
    if st.button("🎧 開始聽打分析"):
        if uploaded_file:
            with st.spinner('上傳與處理中，這可能需要幾分鐘...'):
                try:
                    # 儲存暫存檔
                    temp_file_path = uploaded_file.name
                    with open(temp_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    st.toast("檔案上傳中，請稍候...")
                    audio_file = genai.upload_file(path=temp_file_path)
                    
                    # 讀取秒數改回最快的 2 秒
                    while audio_file.state.name == "PROCESSING":
                        time.sleep(2)
                        audio_file = genai.get_file(audio_file.name)
                        
                    if audio_file.state.name == "FAILED":
                        st.error("Google 伺服器解析檔案失敗，請確認檔案格式是否損毀。")
                        st.stop()
                    
                    st.toast("檔案解析完成！AI 開始聽打中...")
                    model = genai.GenerativeModel(selected_model_name)
                    
                    if fast_mode:
                        # ---------------- 極速版 Prompt ----------------
                        if "1." in task_option:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞（如：喔、啊、呃、那個、對對對）、結巴或重複字詞。若遇到收音不清、長時間空白或背景雜音，請直接略過，絕對禁止無限重複同一個字或詞。

                            1. 【中文逐字稿】：產出高準確度且語句通順的中文逐字稿。
                               - 語者辨識：請務必分辨不同的說話者（例如標註為「記者：」、「受訪者A：」、「受訪者B：」或實際稱呼）。
                               - 排版分段：只要「換人說話」，或是「同一人發言內容過長（超過 3 到 4 句）」，請務必「換行分段」呈現，絕對不要把所有文字濃縮擠成一大塊。
                            """
                        else:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞（如：喔、啊、呃、那個、對對對）、結巴或重複字詞。若遇到收音不清、長時間空白或背景雜音，請直接略過，絕對禁止無限重複同一個字或詞。

                            1. 【雙語比對逐字稿】：自動辨識音檔中的原始語言，產出精確的「原文逐字稿」。
                               - 語者辨識：請務必分辨不同的說話者（例如標註為「記者：」、「受訪者A：」等）。
                               - 排版分段：只要換人說話就必須換行。在每一個原文段落的正下方，請直接提供對應的「中文翻譯」。不同語者的發言區塊之間，請務必「空一行」隔開，保持版面清爽適讀。
                            """
                    else:
                        # ---------------- 完整版 Prompt (含重點與標題) ----------------
                        if "1." in task_option:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下三項任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞（如：喔、啊、呃、那個、對對對）、結巴或重複字詞。若遇到收音不清、長時間空白或背景雜音，請直接略過，絕對禁止無限重複同一個字或詞。

                            1. 【中文逐字稿】：產出高準確度且語句通順的中文逐字稿。
                               - 語者辨識：請務必分辨不同的說話者（例如標註為「記者：」、「受訪者A：」、「受訪者B：」或實際稱呼）。
                               - 排版分段：只要「換人說話」，或是「同一人發言內容過長（超過 3 到 4 句）」，請務必「換行分段」呈現，絕對不要把所有文字濃縮擠成一大塊。
                            2. 【重點條列】：根據逐字稿內容，精煉並條列出核心重點。
                            3. 【電視新聞標題】：根據音檔核心內容，生成 3 個具備「電視新聞感」的標題。
                               - 風格要求：需具備張力與吸引力，精準抓出新聞衝突點、爆點或受訪者金句。
                               - 格式要求：每個標題字數嚴格限制在「15 到 17 個字」以內。標題斷句請使用「全形空白」取代逗號（，），句末絕對不加句號。
                            """
                        else:
                            prompt_text = """
                            請詳細聆聽這段音檔，並嚴格執行以下三項任務。
                            【聽打特別規範】：請自動過濾無意義的語助詞（如：喔、啊、呃、那個、對對對）、結巴或重複字詞。若遇到收音不清、長時間空白或背景雜音，請直接略過，絕對禁止無限重複同一個字或詞。

                            1. 【雙語比對逐字稿】：自動辨識音檔中的原始語言，產出精確的「原文逐字稿」。
                               - 語者辨識：請務必分辨不同的說話者（例如標註為「記者：」、「受訪者A：」等）。
                               - 排版分段：只要換人說話就必須換行。在每一個原文段落的正下方，請直接提供對應的「中文翻譯」。不同語者的發言區塊之間，請務必「空一行」隔開，保持版面清爽適讀。
                            2. 【中文重點條列】：總結音檔內容，條列出中文核心重點。
                            3. 【電視新聞標題】：根據音檔核心內容，生成 3 個具備「電視新聞感」的中文標題。
                               - 風格要求：需具備張力與吸引力，精準抓出新聞衝突點、爆點或受訪者金句。
                               - 格式要求：每個標題字數嚴格限制在「15 到 17 個字」以內。標題斷句請使用「全形空白」取代逗號（，），句末絕對不加句號。
                            """
                    
                    response = model.generate_content([audio_file, prompt_text])
                    
                    st.markdown("### 📝 聽打結果：")
                    st.write(response.text)
                    
                    # 清理本地暫存檔
                    os.remove(temp_file_path)
                    # 清理雲端暫存檔，確保下次不會讀取到錯誤的歷史音檔
                    genai.delete_file(audio_file.name)
                    
                except Exception as e:
                    st.error(f"生成失敗，錯誤原因：{e}")



