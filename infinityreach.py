import sqlite3
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Replace these with your own Telegram API credentials
API_ID = "20899504"
API_HASH = "0fe148b9c0bf4c10dd3eb2e371fda15d"
BOT_TOKEN = "7246016772:AAGL5cp8yY9zvHyYG0so41W5zaBwcW2Uq0M"

# Initialize the bot
app = Client("YouTubeLinkBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database setup
conn = sqlite3.connect("clicks.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    youtube_link TEXT,
    required_clicks INTEGER,
    completed_clicks INTEGER,
    required_subscribers INTEGER,
    completed_subscribers INTEGER,
    required_likes INTEGER,
    completed_likes INTEGER
)
""")
conn.commit()

# YouTube link validation function
def is_youtube_link(link):
    return bool(re.match(r"https?://(www\.)?(youtube\.com|youtu\.be)/", link))

# Start command with buttons
@app.on_message(filters.command("start"))
def start(client, message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Subscribe", callback_data="subscribe"),
                InlineKeyboardButton("Like", callback_data="like")
            ]
        ]
    )
    message.reply_text(
        "👋 Welcome! Select an action to continue.\n\n"
        "You can choose either to subscribe or like a video.",
        reply_markup=keyboard
    )

# Handle button clicks (subscribe or like)
@app.on_callback_query(filters.regex("subscribe"))
def subscribe(client, callback_query):
    callback_query.answer("You have selected to subscribe! ✅")
    callback_query.message.reply_text("How many subscribers do you need to complete your task? (Enter a number)")

    # Store the action to be completed in user's data
    user_id = callback_query.from_user.id
    cursor.execute("UPDATE users SET required_subscribers = NULL WHERE user_id = ?", (user_id,))
    conn.commit()

@app.on_callback_query(filters.regex("like"))
def like(client, callback_query):
    callback_query.answer("You have selected to like! 👍")
    callback_query.message.reply_text("How many likes do you need to complete your task? (Enter a number)")

    # Store the action to be completed in user's data
    user_id = callback_query.from_user.id
    cursor.execute("UPDATE users SET required_likes = NULL WHERE user_id = ?", (user_id,))
    conn.commit()

# Add YouTube link function
@app.on_message(filters.command("addlink"))
def add_link(client, message):
    try:
        args = message.text.split()
        if len(args) != 3:
            message.reply_text("❌ Incorrect format! Use: `/addlink <YouTube_Link> <Required_Clicks>`")
            return

        youtube_link, required_clicks = args[1], int(args[2])

        if not is_youtube_link(youtube_link):
            message.reply_text("❌ Only YouTube links are allowed!")
            return

        user_id = message.from_user.id

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("UPDATE users SET youtube_link = ?, required_clicks = ?, completed_clicks = 0 WHERE user_id = ?",
                           (youtube_link, required_clicks, user_id))
        else:
            cursor.execute("INSERT INTO users (user_id, youtube_link, required_clicks, completed_clicks) VALUES (?, ?, ?, 0)",
                           (user_id, youtube_link, required_clicks))

        conn.commit()
        message.reply_text(f"✅ Your link {youtube_link} has been added with {required_clicks} required clicks.\nNow start clicking other links to get yours promoted!")

    except Exception as e:
        message.reply_text(f"⚠️ Error: {str(e)}")

# Handle user input for required likes or subscribers
@app.on_message(filters.text)
def handle_required_actions(client, message):
    user_id = message.from_user.id
    text = message.text

    # Handle likes requirement
    if text.isdigit() and cursor.execute("SELECT required_likes FROM users WHERE user_id = ?", (user_id,)).fetchone()[0] is None:
        required_likes = int(text)
        cursor.execute("UPDATE users SET required_likes = ? WHERE user_id = ?", (required_likes, user_id))
        conn.commit()
        message.reply_text(f"✅ You need {required_likes} likes to complete your task. Now, please like other links to earn your likes.")

    # Handle subscribers requirement
    elif text.isdigit() and cursor.execute("SELECT required_subscribers FROM users WHERE user_id = ?", (user_id,)).fetchone()[0] is None:
        required_subscribers = int(text)
        cursor.execute("UPDATE users SET required_subscribers = ? WHERE user_id = ?", (required_subscribers, user_id))
        conn.commit()
        message.reply_text(f"✅ You need {required_subscribers} subscribers to complete your task. Now, please subscribe to other channels to earn your subscribers.")

# Confirm clicks function (Loop System Improvement)
@app.on_message(filters.command("confirm"))
def confirm_clicks(client, message):
    user_id = message.from_user.id
    cursor.execute("SELECT required_clicks, completed_clicks FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()

    if not data:
        message.reply_text("❌ You haven't added any link yet! Use /addlink first.")
        return

    required, completed = data
    if completed >= required:
        message.reply_text("✅ You've already completed your required clicks!")
        return

    cursor.execute("UPDATE users SET completed_clicks = completed_clicks + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

    cursor.execute("SELECT completed_clicks FROM users WHERE user_id = ?", (user_id,))
    updated_clicks = cursor.fetchone()[0]

    if updated_clicks >= required:
        message.reply_text("🎉 You've completed your requirement! Your link will now be shared automatically.")
        send_user_link(client, message)
    else:
        message.reply_text(f"✅ Click confirmed! {updated_clicks}/{required} clicks done.")

# Function to automatically share user's link
def send_user_link(client, message):
    user_id = message.from_user.id
    cursor.execute("SELECT youtube_link FROM users WHERE user_id = ?", (user_id,))
    user_link = cursor.fetchone()

    if user_link:
        message.reply_text(f"🚀 Your YouTube link is now being shared:\n🔗 {user_link[0]}")

# Auto-loop system to resend links
@app.on_message(filters.command("resend"))
def resend_links(client, message):
    user_id = message.from_user.id
    cursor.execute("SELECT youtube_link, required_clicks, completed_clicks FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        message.reply_text("❌ You haven't added any link yet! Use /addlink first.")
        return

    youtube_link, required, completed = user_data

    if completed < required:
        message.reply_text(f"⚠️ You need {required - completed} more clicks before resending.")
    else:
        message.reply_text(f"🚀 Your YouTube link is now being re-shared:\n🔗 {youtube_link}")

# Run the bot
app.run()
