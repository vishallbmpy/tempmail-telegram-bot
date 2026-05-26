import telebot
import requests
import time
import threading

TOKEN = "8694604276:AAEhBEF8LTvV3kOd-PoKy_2zLhSxaDpuUqA"
bot = telebot.TeleBot(TOKEN)

user_data = {}
auto_running = {}

# ---------- GET EMAIL BODY (IMPORTANT FIX) ----------
def get_mailtm_message(token, msg_id):
    r = requests.get(
        f"https://api.mail.tm/messages/{msg_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return r.json()


# ---------- CHECK INBOX ----------
def check_inbox(chat_id):
    token = user_data[chat_id]["token"]

    r = requests.get(
        "https://api.mail.tm/messages",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    messages = r.get("hydra:member", [])

    if not messages:
        return None

    msg = messages[0]

    # 🔥 IMPORTANT FIX: FULL MESSAGE BODY GET
    full = get_mailtm_message(token, msg["id"])

    return {
        "subject": msg["subject"],
        "body": full.get("text", "No body found")
    }


# ---------- AUTO LOOP (FIXED STOP SYSTEM) ----------
def auto_loop(chat_id):

    auto_running[chat_id] = True

    for i in range(20):

        if not auto_running.get(chat_id):
            bot.send_message(chat_id, "🛑 Auto stopped")
            return

        result = check_inbox(chat_id)

        if result:

            # 🔥 SMART OTP FILTER
            text = result["subject"] + " " + result["body"]

            if any(x in text.lower() for x in ["otp", "code", "verification"]):

                bot.send_message(
                    chat_id,
                    f"📩 OTP FOUND:\n\n"
                    f"Subject: {result['subject']}\n\n"
                    f"Body: {result['body'][:300]}"
                )
                return

        bot.send_message(chat_id, "🔄 checking...")
        time.sleep(5)

    bot.send_message(chat_id, "❌ OTP not received")


# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id,
        "🤖 Temp Mail Bot\n\n/new → email\n/check → OTP\n/auto → start\n/stop → stop auto"
    )


# ---------- NEW EMAIL ----------
@bot.message_handler(commands=['new'])
def new(m):
    domain = requests.get("https://api.mail.tm/domains").json()["hydra:member"][0]["domain"]

    email = f"user{int(time.time())}@{domain}"
    password = "Test@12345"

    requests.post("https://api.mail.tm/accounts", json={
        "address": email,
        "password": password
    })

    token = requests.post("https://api.mail.tm/token", json={
        "address": email,
        "password": password
    }).json()["token"]

    user_data[m.chat.id] = {
        "email": email,
        "token": token
    }

    bot.send_message(m.chat.id, f"📧 Email:\n\n{email}")


# ---------- CHECK ----------
@bot.message_handler(commands=['check'])
def check(m):

    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ पहले /new करो")
        return

    result = check_inbox(m.chat.id)

    if not result:
        bot.send_message(m.chat.id, "📭 No OTP yet")
        return

    bot.send_message(
        m.chat.id,
        f"📩 OTP:\n\n{result['subject']}\n\n{result['body'][:300]}"
    )


# ---------- AUTO START ----------
@bot.message_handler(commands=['auto'])
def auto(m):

    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ पहले /new करो")
        return

    if auto_running.get(m.chat.id):
        bot.send_message(m.chat.id, "⚠️ Already running")
        return

    bot.send_message(m.chat.id, "🔄 Auto started")

    threading.Thread(target=auto_loop, args=(m.chat.id,)).start()


# ---------- STOP ----------
@bot.message_handler(commands=['stop'])
def stop(m):
    auto_running[m.chat.id] = False
    bot.send_message(m.chat.id, "🛑 Stopping auto...")


bot.polling()
