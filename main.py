import csv
import re
import random
import warnings
import os
import urllib.request
import urllib.parse
import json
import threading
import concurrent.futures
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import traceback
import time
import customtkinter as ctk 
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import fugashi
import genanki
import sys

warnings.filterwarnings('ignore', category=UserWarning, module='ebooklib')

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def get_resource_path(relative_path):
    if os.path.isabs(relative_path):
        return relative_path
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ==========================================
# 核心业务逻辑
# ==========================================
def load_vocab(csv_path):
    vocab_dict = {}
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            lines =[line.replace('，', ',') for line in f]
    except UnicodeDecodeError:
        with open(csv_path, 'r', encoding='gbk') as f:
            lines =[line.replace('，', ',') for line in f]
        
    reader = csv.reader(lines)
    for row in reader:
        if not row: continue
        word = row[0].strip()
        if word == "日语词汇" or "单词" in word: continue
            
        if len(row) >= 3:
            reading = row[1].strip()
            meaning = row[2].strip()
            vocab_dict[word] = f"[{reading}] {meaning}"
        elif len(row) == 2:
            vocab_dict[word] = row[1].strip()
    return vocab_dict

def extract_sentences_from_epub(epub_path):
    book = epub.read_epub(epub_path)
    sentences =[]
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        raw_sentences = re.split(r'(?<=[。！？])', text)
        for s in raw_sentences:
            s = s.strip()
            if 5 < len(s) < 150: sentences.append(s)
    return sentences

def find_vocab_in_sentences(sentences, vocab_dict):
    tagger = fugashi.Tagger()
    try:
        matched_data = {}
        for sentence in sentences:
            for word in tagger(sentence):
                lemma = getattr(word.feature, 'lemma', None)
                if not lemma: lemma = word.surface
                lemma = lemma.split('-')[0]

                if lemma in vocab_dict and lemma not in matched_data:
                    highlighted_sentence = sentence.replace(word.surface, f"<b style='color:#e74c3c;'>{word.surface}</b>")
                    matched_data[lemma] = {
                        "word": lemma,
                        "meaning": vocab_dict[lemma],
                        "sentence": highlighted_sentence,
                        "clean_sentence": sentence 
                    }
        return list(matched_data.values())
    finally:
        del tagger

# ==========================================
# 片假名提取与【中英双语】翻译模块
# ==========================================
def find_katakana_in_sentences(sentences, existing_words_set):
    tagger = fugashi.Tagger()
    katakana_data = {}
    kata_pattern = re.compile(r'^[\u30A0-\u30FC]{2,}$')
    
    try:
        for sentence in sentences:
            for word in tagger(sentence):
                surface = word.surface
                if kata_pattern.match(surface) and surface not in existing_words_set and surface not in katakana_data:
                    highlighted_sentence = sentence.replace(surface, f"<b style='color:#9b59b6;'>{surface}</b>")
                    katakana_data[surface] = {
                        "word": surface, "meaning": "", 
                        "sentence": highlighted_sentence, "clean_sentence": sentence
                    }
        return list(katakana_data.values())
    finally:
        del tagger

def fetch_bilingual_meaning(word):
    """免翻墙版：联合调用 Jisho(找英语) + 有道翻译(日翻中)"""
    en_meaning = ""
    # 第一步：去 Jisho 查纯正的英文意思 (Jisho 官网在国内一般可以直接访问)
    try:
        url = f"https://jisho.org/api/v1/search/words?keyword={urllib.parse.quote(word)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=3).read().decode('utf-8')
        data = json.loads(response)
        if data['data']:
            senses = data['data'][0].get('senses',[])
            if senses and senses[0].get('english_definitions'):
                en_meaning = ", ".join(senses[0]['english_definitions'][:2])
    except Exception:
        pass

    # 第二步：调用国内的【有道翻译】免费接口，直接翻译为中文
    zh_meaning = ""
    try:
        # 有道公开的 GET 接口
        yd_url = f"http://fanyi.youdao.com/translate?&doctype=json&type=JA2ZH_CN&i={urllib.parse.quote(word)}"
        yd_req = urllib.request.Request(yd_url, headers={'User-Agent': 'Mozilla/5.0'})
        yd_resp = urllib.request.urlopen(yd_req, timeout=3).read().decode('utf-8')
        yd_data = json.loads(yd_resp)
        zh_meaning = yd_data['translateResult'][0][0]['tgt']
        
        # 如果有道翻译不出来，会原样返回日文假名，我们就当它没查到
        if zh_meaning == word:
            zh_meaning = ""
    except Exception:
        pass

    # 第三步：智能拼接组合
    if zh_meaning and en_meaning:
        return f"{zh_meaning} ({en_meaning})"
    elif zh_meaning:
        return zh_meaning
    elif en_meaning:
        return en_meaning
    else:
        return "专有名词 / 无释义"

def translate_katakana_batch(katakana_list, progress_callback):
    total = len(katakana_list)
    completed = 0
    
    def process_item(item):
        # 【极其关键的优化】：加入 0.2 秒延迟，防止多线程并发过猛被有道暂时封禁 IP
        time.sleep(0.2)
        meaning = fetch_bilingual_meaning(item['word'])
        item['meaning'] = f"[外] {meaning}"
        return item

    # 使用 5 个线程并发查询，速度快且安全
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_item = {executor.submit(process_item, item): item for item in katakana_list}
        for future in concurrent.futures.as_completed(future_to_item):
            completed += 1
            progress_callback(completed, total)
            
    return katakana_list

# ==========================================
# 导出与 API
# ==========================================
def create_anki_deck(deck_name, matched_list, output_path):
    model_id = random.randrange(1 << 30, 1 << 31)
    deck_id = random.randrange(1 << 30, 1 << 31)
    my_model = genanki.Model(
        model_id, 'YomiKomi 小说专属单词卡',
        fields=[{'name': 'Word'}, {'name': 'Sentence'}, {'name': 'Meaning'}],
        templates=[{
            'name': 'Card 1',
            'qfmt': '<div style="font-size:40px; font-weight:bold; margin-bottom: 20px;">{{Word}}</div><div style="font-size:20px; color:#555; text-align:left; border-left: 4px solid #ccc; padding-left: 10px;">{{Sentence}}</div>',
            'afmt': '{{FrontSide}}<hr id="answer"><div style="font-size:26px; color:#2980b9;">{{Meaning}}</div>',
        }],
        css='.card { font-family: "Hiragino Sans", "Meiryo", sans-serif; text-align: center; color: #333; background-color: #fdfdfd; }'
    )
    my_deck = genanki.Deck(deck_id, deck_name)
    for item in matched_list:
        my_deck.add_note(genanki.Note(model=my_model, fields=[item['word'], item['sentence'], item['meaning']]))
    genanki.Package(my_deck).write_to_file(output_path)

def export_to_csv(matched_list, output_path):
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['单词', '释义', '小说例句']) 
        for item in matched_list: writer.writerow([item['word'], item['meaning'], item['clean_sentence']])

def export_to_txt(deck_name, matched_list, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"【{deck_name}】\n" + "=" * 40 + "\n\n")
        for i, item in enumerate(matched_list, 1):
            f.write(f"{i}. {item['word']}  {item['meaning']}\n   例句：{item['clean_sentence']}\n" + "-" * 40 + "\n")

def import_to_anki_api(apkg_path):
    payload = {"action": "importPackage", "version": 6, "params": {"path": os.path.abspath(apkg_path).replace('\\', '/')}}
    try:
        req = urllib.request.Request('http://127.0.0.1:8765', json.dumps(payload).encode('utf-8'))
        response = json.loads(urllib.request.urlopen(req, timeout=3).read().decode('utf-8'))
        if response.get('error'): return False, f"❌ Anki 内部报错: {response['error']}"
        return True, "✅ 成功触发 Anki API！卡片已无缝注入！"
    except Exception as e: return False, f"❌ API 发生未知错误: {str(e)}"

# ==========================================
# 现代化 GUI 界面
# ==========================================
class YomiKomiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YomiKomi 沉浸式日语背词器")
        self.geometry("650x850") 
        self.epub_path = ""
        self.vocab_options = {
            "🎯 N1 核心词汇": "dicts/n1_vocab.csv",
            "🎯 N2 重点词汇": "dicts/n2_vocab.csv",
            "🎯 N2 重点词汇 (扩展版)": "dicts/n2_vocab_extended.csv",
            "🎯 N3 基础词汇": "dicts/n3_vocab.csv"
        }

        ctk.CTkLabel(self, text="📚 YomiKomi", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self, text="将轻小说转化为你的专属记忆库", text_color="gray").pack(pady=(0, 15))

        frame = ctk.CTkFrame(self)
        frame.pack(pady=10, padx=20, fill="x")

        # 1. 词库选择
        ctk.CTkLabel(frame, text="1. 选择目标词库:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.vocab_combo = ctk.CTkOptionMenu(frame, values=list(self.vocab_options.keys()), width=200)
        self.vocab_combo.grid(row=0, column=1, padx=(10, 5), pady=15, sticky="w")
        ctk.CTkButton(frame, text="➕ 导入自定义", width=80, command=self.add_custom_vocab, fg_color="#8e44ad", hover_color="#9b59b6").grid(row=0, column=2, padx=(5, 15), pady=15, sticky="w")

        # 2. 小说选择
        ctk.CTkLabel(frame, text="2. 选择 EPUB 小说:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=15, pady=15, sticky="w")
        ctk.CTkButton(frame, text="📁 浏览文件...", width=200, command=self.select_epub, fg_color="#2ecc71", hover_color="#27ae60").grid(row=1, column=1, padx=(10, 5), pady=15, sticky="w")
        self.lbl_epub_path = ctk.CTkLabel(frame, text="尚未选择小说...", text_color="gray", width=200, anchor="w")
        self.lbl_epub_path.grid(row=2, column=1, columnspan=2, padx=(10, 5), pady=(0, 15), sticky="w")

        # 3. 附加格式
        ctk.CTkLabel(frame, text="3. 选择生成格式:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=15, pady=(0, 15), sticky="w")
        self.export_anki_var = ctk.BooleanVar(value=True) 
        self.export_csv_var = ctk.BooleanVar(value=False)
        self.export_txt_var = ctk.BooleanVar(value=False)
        checkbox_frame = ctk.CTkFrame(frame, fg_color="transparent")
        checkbox_frame.grid(row=3, column=1, columnspan=2, padx=(5, 0), pady=(0, 15), sticky="w")
        ctk.CTkCheckBox(checkbox_frame, text="Anki包(.apkg)", variable=self.export_anki_var).pack(side="left", padx=(5, 10))
        ctk.CTkCheckBox(checkbox_frame, text="Excel(.csv)", variable=self.export_csv_var).pack(side="left", padx=10)
        ctk.CTkCheckBox(checkbox_frame, text="纯文本(.txt)", variable=self.export_txt_var).pack(side="left", padx=10)

        # 4. 高阶增强功能
        ctk.CTkLabel(frame, text="4. 高阶增强扫描:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=15, pady=(0, 15), sticky="w")
        self.extract_katakana_var = ctk.BooleanVar(value=True) 
        ctk.CTkCheckBox(frame, text="🤖 提取外来语 (并自动翻译成 中英双语)", variable=self.extract_katakana_var, text_color="#d35400").grid(row=4, column=1, columnspan=2, padx=(5, 0), pady=(0, 15), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate")
        self.progress_bar.pack(pady=(15, 5), padx=40, fill="x")
        self.progress_bar.set(0)

        self.btn_run = ctk.CTkButton(self, text="⚡ 立即提取词汇并导出", command=self.start_processing, height=45, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_run.pack(pady=10)

        self.log_textbox = ctk.CTkTextbox(self, height=120, state="disabled", font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.pack(pady=10, padx=20, fill="both", expand=True)
        self.log("系统就绪。勾选 [外来语提取] 需要连接网络，请耐心等待！")

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_textbox.see("end")  
        self.log_textbox.configure(state="disabled")

    def add_custom_vocab(self):
        file_path = filedialog.askopenfilename(title="选择你的自定义词库", filetypes=[("CSV 文件", "*.csv")])
        if file_path:
            vocab_name = f"🌟 {os.path.splitext(os.path.basename(file_path))[0]}"
            self.vocab_options[vocab_name] = file_path
            self.vocab_combo.configure(values=list(self.vocab_options.keys()))
            self.vocab_combo.set(vocab_name)
            self.log(f"成功导入自定义词库: {vocab_name}")

    def select_epub(self):
        file_path = filedialog.askopenfilename(title="选择轻小说", filetypes=[("EPUB 文件", "*.epub")])
        if file_path:
            self.epub_path = file_path
            self.lbl_epub_path.configure(text=os.path.basename(file_path), text_color=("black", "white"))
            self.log(f"已选中小说: {os.path.basename(file_path)}")

    def start_processing(self):
        if not self.epub_path: return self.log("⚠️ 警告：请先选择一本 EPUB 小说！")
        if not (self.export_anki_var.get() or self.export_csv_var.get() or self.export_txt_var.get()):
            return messagebox.showwarning("格式错误", "请至少勾选一种导出格式！")
                
        real_csv_path = get_resource_path(self.vocab_options[self.vocab_combo.get()])
        if not os.path.exists(real_csv_path): return self.log(f"❌ 严重错误：找不到词库文件 {real_csv_path}")
        
        self.btn_run.configure(state="disabled", text="正在疯狂运转中...")
        self.progress_bar.set(0)
        self.log("-" * 40 + "\n🚀 启动自动化流水线...")    
        threading.Thread(target=self.process_thread, args=(real_csv_path,), daemon=True).start()

    def process_thread(self, csv_file_name):
        try:
            novel_name = os.path.splitext(os.path.basename(self.epub_path))[0]
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', novel_name)
            epub_dir = os.path.dirname(os.path.abspath(self.epub_path))
            output_apkg = os.path.join(epub_dir, f"{safe_name}_专属词汇.apkg")
            output_csv  = os.path.join(epub_dir, f"{safe_name}_专属词汇.csv")
            output_txt  = os.path.join(epub_dir, f"{safe_name}_专属词汇.txt")
            deck_name = f"📚《{novel_name}》阅读突破"

            self.after(0, lambda: self.progress_bar.set(0.1))
            self.after(0, lambda: self.log(f"📦 正在加载目标核心词库..."))
            vocab = load_vocab(csv_file_name)
            
            self.after(0, lambda: self.progress_bar.set(0.2))
            self.after(0, lambda: self.log("📖 正在解析 EPUB 小说结构..."))
            sentences = extract_sentences_from_epub(self.epub_path)
            
            self.after(0, lambda: self.progress_bar.set(0.3))
            self.after(0, lambda: self.log(f"✂️ 共提取 {len(sentences)} 句有效原句。"))
            self.after(0, lambda: self.log("🧠 正在匹配您的核心词库..."))
            matched = find_vocab_in_sentences(sentences, vocab)
            
            if self.extract_katakana_var.get():
                self.after(0, lambda: self.log("🤖 开启外来语雷达：扫描全书片假名..."))
                katakana_matches = find_katakana_in_sentences(sentences, {item['word'] for item in matched})
                if katakana_matches:
                    total_k = len(katakana_matches)
                    self.after(0, lambda: self.log(f"🌍 发现 {total_k} 个片假名词汇！启动多线程 【中英双语】 翻译..."))
                    
                    def update_k_progress(completed, total):
                        self.after(0, lambda: self.progress_bar.set(0.3 + 0.4 * (completed / total)))
                        if completed % 20 == 0 or completed == total:
                            self.after(0, lambda: self.log(f"   翻译进度: {completed}/{total} ..."))
                            
                    katakana_matches = translate_katakana_batch(katakana_matches, update_k_progress)
                    matched.extend(katakana_matches)
                    self.after(0, lambda: self.log("✅ 翻译完成！已无缝融合进您的专属词汇本。"))
                else:
                    self.after(0, lambda: self.log("🤖 全书中没有发现多余的外来语词汇。"))
            else:
                self.after(0, lambda: self.progress_bar.set(0.7))

            if not matched:
                self.after(0, lambda: self.progress_bar.set(1.0))
                self.after(0, lambda: self.log("⚠️ 匹配结束：没有找到任何词汇。"))
                return
            
            self.after(0, lambda: self.progress_bar.set(0.8))
            self.after(0, lambda: self.log(f"🎯 数据组装完毕！共 {len(matched)} 个卡片。"))
            
            export_msg_parts =[]
            if self.export_anki_var.get():
                self.after(0, lambda: self.log(f"🪄 打包 Anki 文件..."))
                create_anki_deck(deck_name, matched, output_apkg)
                api_success, api_msg = import_to_anki_api(output_apkg)
                self.after(0, lambda: self.log(api_msg))
                if api_success: export_msg_parts.append("✅ Anki包自动注入")
                else: export_msg_parts.append("⚠️ Anki包生成 (但未自动注入，可双击导入)")

            if self.export_csv_var.get():
                export_to_csv(matched, output_csv)
                export_msg_parts.append("✅ CSV 表格")

            if self.export_txt_var.get():
                export_to_txt(deck_name, matched, output_txt)
                export_msg_parts.append("✅ TXT 文本")

            self.after(0, lambda: self.progress_bar.set(1.0))
            self.after(0, lambda: self.log("🎉 全部导出流程完美结束！"))
            self.after(0, lambda m=f"🎉 成功提取 {len(matched)} 个词汇！\n\n" + "\n".join(export_msg_parts): messagebox.showinfo("提取完成", m))

        except Exception as e:
            traceback.print_exc()
            self.after(0, lambda msg=f"❌ 运行崩溃：{str(e)}": self.log(msg))
            self.after(0, lambda: self.progress_bar.set(0))
        finally:
            self.after(0, lambda: self.btn_run.configure(state="normal", text="⚡ 立即提取词汇并导出"))

if __name__ == '__main__':
    app = YomiKomiApp()
    app.mainloop()