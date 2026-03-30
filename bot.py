import telebot
import re
import time
import os
import json
from flask import Flask
import threading

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
SUPER_OWNER = int(os.getenv("SUPER_OWNER"))

bot = telebot.TeleBot(TOKEN)

# ================= FILE =================
OWNER_FILE = "owners.json"

def load_owners():
    if os.path.exists(OWNER_FILE):
        with open(OWNER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_owners():
    with open(OWNER_FILE, "w") as f:
        json.dump(owners, f)

owners = load_owners()

# ================= FLASK =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Alive 🔥"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ================= DATA =================
group_start = {}
warnings = {}

TRIAL_DAYS = 7

stats = {"total": 0, "deleted": 0}

# ================= FILTERS =================
def is_promotion(text):
    if not text:
        return False
    text = text.lower()
    patterns = [r"http[s]?://", r"www\.", r"\.com", r"t\.me"]
    return any(re.search(p, text) for p in patterns)

def is_abusive(text):
    if not text:
        return False
    bad_words = ["mc","bc","madarchod","behenchod","gandu","chutiya","fuck"]
    return any(w in text.lower() for w in bad_words)

# ================= TRIAL =================
def is_trial_active(chat_id):
    chat_id = str(chat_id)
    if chat_id not in group_start:
        group_start[chat_id] = time.time()
        return True
    return (time.time() - group_start[chat_id]) < TRIAL_DAYS * 86400

# ================= SET OWNER =================
@bot.message_handler(commands=["setowner"])
def set_owner(message):
    chat_id = str(message.chat.id)
    user_id = message.from_user.id

    if user_id != SUPER_OWNER:
        owners[chat_id] = user_id
        save_owners()
        bot.reply_to(message, "👑 Owner set permanently!")
    else:
        bot.reply_to(message, "⚠️ You are super owner already!")

# ================= RULES =================
@bot.message_handler(commands=["rules"])
def rules_cmd(message):
    bot.send_message(message.chat.id,
"""📜 Rules:
❌ No links
❌ No promotion
❌ No abuse
⚠️ 3 warnings = Kick""")

# ================= WELCOME =================
@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):
    for user in message.new_chat_members:
        bot.send_message(
            message.chat.id,
            f"👋 Welcome {user.first_name}!\nType /rules"
        )

# ================= WARNING =================
def add_warning(chat_id, user_id):
    key = (str(chat_id), user_id)
    warnings[key] = warnings.get(key, 0) + 1
    return warnings[key]

# ================= MAIN =================
@bot.message_handler(func=lambda message: True)
def handle(message):
    chat_id = str(message.chat.id)
    user_id = message.from_user.id
    text = message.text or ""

    stats["total"] += 1

    # Trial
    if not is_trial_active(chat_id):
        bot.send_message(chat_id, "❌ Trial expired")
        return

    # Owner bypass
    if user_id == SUPER_OWNER or (chat_id in owners and user_id == owners[chat_id]):
        return

    # Filter
    if is_promotion(text) or is_abusive(text):
        try:
            bot.delete_message(chat_id, message.message_id)
            stats["deleted"] += 1

            count = add_warning(chat_id, user_id)

            if count >= 3:
                bot.kick_chat_member(chat_id, user_id)
                bot.send_message(chat_id, "🚫 User kicked")
            else:
                bot.send_message(chat_id, f"⚠️ Warning {count}/3")
        except:
            pass

# ================= STATS =================
@bot.message_handler(commands=["stats"])
def stats_cmd(message):
    chat_id = str(message.chat.id)
    user_id = message.from_user.id

    if user_id == SUPER_OWNER or (chat_id in owners and user_id == owners[chat_id]):
        bot.send_message(chat_id,
f"""📊 Stats
Total: {stats['total']}
Deleted: {stats['deleted']}""")

# ================= RUN =================
threading.Thread(target=run_flask).start()

print("🔥 Bot Running...")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
