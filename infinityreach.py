import sqlite3
import re
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Telegram API credentials
API_ID = "20899504"
API_HASH = "0fe148b9c0bf4c10dd3eb2e371fda15d"
BOT_TOKEN = "7246016772:AAGL5cp8yY9zvHyYG0so41W5zaBwcW2Uq0M"

# Initialize bot
app = Client("YouTubeTaskBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database setup
conn = sqlite3.connect("tasks.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS likes (
    user_id INTEGER PRIMARY KEY,
    youtube_link TEXT,
    required_likes INTEGER,
    completed_likes INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS subscribers (
    user_id INTEGER PRIMARY KEY,
    youtube_link TEXT,
    required_subscribers INTEGER,
    completed_subscribers INTEGER DEFAULT 0
)
""")
conn.commit()

# YouTube link validation
def is_youtube_link(link):
    return bool(re.match(r"https?://(www\.)?(youtube\.com|youtu\.be)/", link))

# User data storage
user_data = {}

# Start command
@app.on_message(filters.command("start"))
def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Subscribe", callback_data="subscribe"),
         InlineKeyboardButton("Like", callback_data="like")]
    ])
    message.reply_text("\U0001F44B Welcome! Choose an action:", reply_markup=keyboard)

# Handle Subscribe and Like selection
@app.on_callback_query(filters.regex("subscribe"))
def subscribe(client, callback_query):
    user_data[callback_query.from_user.id] = {"action": "subscribe"}
    callback_query.message.reply_text("आपको कितने सब्सक्राइबर्स चाहिए? संख्या डालें।")

@app.on_callback_query(filters.regex("like"))
def like(client, callback_query):
    user_data[callback_query.from_user.id] = {"action": "like"}
    callback_query.message.reply_text("आपको कितने लाइक्स चाहिए? संख्या डालें।")

# Handle user input for likes/subscribers
@app.on_message(filters.text & filters.private)
def handle_count(client, message):
    user_id = message.from_user.id
    action = user_data.get(user_id, {}).get("action")
    
    if not action or not message.text.isdigit():
        return

    count = int(message.text)
    
    if action == "like":
        cursor.execute("SELECT youtube_link FROM likes ORDER BY completed_likes LIMIT ?", (count,))
    elif action == "subscribe":
        cursor.execute("SELECT youtube_link FROM subscribers ORDER BY completed_subscribers LIMIT ?", (count,))
    
    links = cursor.fetchall()
    
    if links:
        response = "\U0001F517 Like or Subscribe these links first:\n" + '\n'.join(link[0] for link in links)
        message.reply_text(response)
        user_data[user_id]["pending_task"] = count
    else:
        message.reply_text("कोई टास्क उपलब्ध नहीं है। बाद में प्रयास करें।")

# Confirm task completion
@app.on_message(filters.command("confirm"))
def confirm_task(client, message):
    user_id = message.from_user.id
    pending_task = user_data.get(user_id, {}).get("pending_task")

    if not pending_task:
        message.reply_text("आपके पास कोई लंबित टास्क नहीं है।")
        return

    action = user_data.get(user_id, {}).get("action")
    
    if action == "like":
        cursor.execute("UPDATE likes SET completed_likes = completed_likes + ? WHERE user_id != ?", (pending_task, user_id))
    elif action == "subscribe":
        cursor.execute("UPDATE subscribers SET completed_subscribers = completed_subscribers + ? WHERE user_id != ?", (pending_task, user_id))
    
    conn.commit()
    message.reply_text("✅ टास्क पूरा हुआ! अब आप अपना लिंक जोड़ सकते हैं। /addlink का उपयोग करें।")
    user_data[user_id]["task_completed"] = True

# Add user link
@app.on_message(filters.command("addlink"))
def add_link(client, message):
    user_id = message.from_user.id
    if not user_data.get(user_id, {}).get("task_completed"):
        message.reply_text("❌ पहले टास्क पूरा करें!")
        return
    
    args = message.text.split()
    if len(args) != 2 or not is_youtube_link(args[1]):
        message.reply_text("❌ गलत प्रारूप! `/addlink <YouTube_Link>` उपयोग करें।")
        return
    
    youtube_link = args[1]
    action = user_data.get(user_id, {}).get("action")
    pending_task = user_data.get(user_id, {}).get("pending_task")
    
    if action == "like":
        cursor.execute("INSERT INTO likes (user_id, youtube_link, required_likes) VALUES (?, ?, ?)", (user_id, youtube_link, pending_task))
    elif action == "subscribe":
        cursor.execute("INSERT INTO subscribers (user_id, youtube_link, required_subscribers) VALUES (?, ?, ?)", (user_id, youtube_link, pending_task))
    
    conn.commit()
    message.reply_text("✅ आपका लिंक जोड़ा गया। जब तक आपके आवश्यक लाइक्स/सब्सक्राइबर नहीं मिल जाते, तब तक यह रहेगा।")
    user_data[user_id]["task_completed"] = False

# Flask Web Server for Render Deployment
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is Running!"

def run_flask():
    app_web.run(host="0.0.0.0", port=8080)

# Start Flask in a separate thread
threading.Thread(target=run_flask, daemon=True).start()

# Run bot
app.run()
