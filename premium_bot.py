import telebot
import requests
import base64
import tempfile
import os
import io
from collections import defaultdict

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8698611330:AAFVSy51MtsK9Hv4g2DqG2vx4M6NnKIYj54"
GROQ_API_KEY = ""

# Model သတ်မှတ်ချက်များ
TEXT_MODEL = "llama-3-70b-8192"
VISION_MODEL = "llama-3.2-11b-vision-preview"
WHISPER_MODEL = "whisper-large-v3"
WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
history = defaultdict(list)
MAX_HIST = 10

# --- HELPER FUNCTIONS ---

def ask_groq(uid, model=TEXT_MODEL):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": history[uid]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error connecting to Groq: {e}"

def add_history(uid, role, content):
    history[uid].append({"role": role, "content": content})
    if len(history[uid]) > MAX_HIST:
        history[uid] = history[uid][-MAX_HIST:]

# --- MESSAGE HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(msg):
    bot.reply_to(msg, "မင်္ဂလာပါ! ကျွန်တော်က Claude-like Premium Bot ပါ။ စာ၊ ဓာတ်ပုံ၊ အသံနဲ့ Document တွေ ပို့ပြီး မေးမြန်းနိုင်ပါတယ်။")

@bot.message_handler(content_types=['text'])
def handle_text(msg):
    uid = msg.from_user.id
    add_history(uid, "user", msg.text)
    bot.send_chat_action(msg.chat.id, "typing")
    reply = ask_groq(uid)
    add_history(uid, "assistant", reply)
    bot.reply_to(msg, reply)

@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    uid     = msg.from_user.id
    caption = msg.caption or "ဒီဓာတ်ပုံထဲမှာ ဘာတွေပါသလဲ ခင်ဗျာ? အသေးစိတ် ဖော်ပြပေးပါ။"
    bot.send_chat_action(msg.chat.id, "typing")
    wait = bot.reply_to(msg, "🖼️ ဓာတ်ပုံ ကြည့်နေပါပြီ ခင်ဗျာ...")
    try:
        file_info = bot.get_file(msg.photo[-1].file_id)
        file_url  = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"
        img_bytes = requests.get(file_url, timeout=30).content
        b64       = base64.b64encode(img_bytes).decode()
        
        # Image content formatting for Vision API
        history[uid].append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": caption},
            ],
        })
        
        reply = ask_groq(uid, VISION_MODEL)
        add_history(uid, "assistant", reply)
        bot.edit_message_text(reply, msg.chat.id, wait.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ ဓာတ်ပုံ Error: {e}", msg.chat.id, wait.message_id)

@bot.message_handler(content_types=["voice"])
def handle_voice(msg):
    uid = msg.from_user.id
    bot.send_chat_action(msg.chat.id, "typing")
    wait = bot.reply_to(msg, "🎤 Voice message နားထောင်နေပါပြီ ခင်ဗျာ...")
    try:
        file_info  = bot.get_file(msg.voice.file_id)
        file_url   = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"
        voice_data = requests.get(file_url, timeout=30).content
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(voice_data)
            tmp_path = f.name
            
        with open(tmp_path, "rb") as audio_file:
            trans = requests.post(
                WHISPER_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": ("voice.ogg", audio_file, "audio/ogg")},
                data={"model": WHISPER_MODEL},
                timeout=60,
            )
        os.unlink(tmp_path)
        text = trans.json().get("text", "").strip()
        
        if not text:
            bot.edit_message_text("⚠️ Voice ကို နားမလည်ဘူး ခင်ဗျာ။", msg.chat.id, wait.message_id)
            return

        add_history(uid, "user", text)
        reply = ask_groq(uid)
        add_history(uid, "assistant", reply)
        final = f"🎤 သင်ပြောတာ: {text}\n\n🤖 ဖြေချက်: {reply}"
        bot.edit_message_text(final, msg.chat.id, wait.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Voice error: {e}", msg.chat.id, wait.message_id)

@bot.message_handler(content_types=["document"])
def handle_document(msg):
    uid     = msg.from_user.id
    caption = msg.caption or "ဒီ document ထဲမှာ ဘာတွေပါသလဲ ခင်ဗျာ? အသေးစိတ် ရှင်းပြပေးပါ။"
    bot.send_chat_action(msg.chat.id, "typing")
    wait = bot.reply_to(msg, "📄 Document ဖတ်နေပါပြီ ခင်ဗျာ...")
    try:
        file_info = bot.get_file(msg.document.file_id)
        file_url  = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"
        file_data = requests.get(file_url, timeout=60).content
        fname     = msg.document.file_name or "file"
        extracted = ""

        if fname.lower().endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_data))
            for page in reader.pages:
                extracted += page.extract_text() or ""
        elif fname.lower().endswith((".txt", ".md", ".py", ".js", ".html", ".csv", ".json")):
            extracted = file_data.decode("utf-8", errors="ignore")
        else:
            bot.edit_message_text("⚠️ PDF သို့မဟုတ် စာသားဖိုင်များပဲ ပို့ပေးပါ ခင်ဗျာ။", msg.chat.id, wait.message_id)
            return

        if not extracted.strip():
            bot.edit_message_text("⚠️ စာသား ရှာမတွေ့ပါဘူး။", msg.chat.id, wait.message_id)
            return

        content = f"Document '{fname}':\n\n{extracted[:5000]}\n\nမေးခွန်း: {caption}"
        add_history(uid, "user", content)
        reply = ask_groq(uid)
        add_history(uid, "assistant", reply)
        bot.edit_message_text(f"📄 {fname}\n\n{reply}", msg.chat.id, wait.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Document error: {e}", msg.chat.id, wait.message_id)

if __name__ == "__main__":
    print("✅ Bot is running...")
    bot.infinity_polling()
