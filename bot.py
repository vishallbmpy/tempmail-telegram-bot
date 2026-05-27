import telebot
import requests
import time
import threading
import os

# ---------------- BOT TOKEN ----------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ BOT_TOKEN not found")
    exit()

bot = telebot.TeleBot(TOKEN)

# ---------------- DATA ----------------
user_data = {}
auto_running = {}

# ---------------- GET FULL MESSAGE ----------------
def get_mailtm_message(token, msg_id):

    try:
        r = requests.get(
            f"https://api.mail.tm/messages/{msg_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        return r.json()

    except Exception as e:
        print("GET MESSAGE ERROR:", e)
        return {}


# ---------------- CHECK INBOX ----------------
def check_inbox(chat_id):

    try:

        token = user_data[chat_id]["token"]

        r = requests.get(
            "https://api.mail.tm/messages",
            headers={"Authorization": f"Bearer {token}"}
        )

        data = r.json()

        messages = data.get("hydra:member", [])

        if not messages:
            return None

        msg = messages[0]

        full = get_mailtm_message(token, msg["id"])

        return {
            "subject": msg.get("subject", "No Subject"),
            "body": full.get("text", "No Body")
        }

    except Exception as e:
        print("CHECK ERROR:", e)
        return None


# ---------------- AUTO LOOP ----------------
def auto_loop(chat_id):

    auto_running[chat_id] = True

    last_subject = ""

    for i in range(60):

        if not auto_running.get(chat_id):
            bot.send_message(chat_id, "🛑 Auto stopped")
            return

        result = check_inbox(chat_id)

        if result:

            subject = result["subject"]
            body = result["body"]

            # duplicate avoid
            if subject == last_subject:
                time.sleep(5)
                continue

            last_subject = subject

            text = (subject + " " + body).lower()

            if any(x in text for x in ["otp", "code", "verification", "login"]):

                bot.send_message(
                    chat_id,
                    f"📩 OTP FOUND\n\n"
                    f"📌 Subject:\n{subject}\n\n"
                    f"📨 Message:\n{body[:500]}"
                )

            else:

                bot.send_message(
                    chat_id,
                    f"📬 New Email\n\n"
                    f"📌 Subject:\n{subject}"
                )

        time.sleep(5)

    bot.send_message(chat_id, "⌛ Auto check finished")


# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(m):

    bot.send_message(
        m.chat.id,
        "🔥 Temp Mail Bot\n\n"
        "/new → New Temp Email\n"
        "/check → Check Inbox\n"
        "/auto → Auto OTP Check\n"
        "/stop → Stop Auto"
    )


# ---------------- NEW EMAIL ----------------
@bot.message_handler(commands=['new'])
def new(m):

    try:

        bot.send_message(m.chat.id, "⏳ Creating Temp Email...")

        domains = requests.get(
            "https://api.mail.tm/domains"
        ).json()

        domain = domains["hydra:member"][0]["domain"]

        email = f"user{int(time.time())}@{domain}"
        password = "Test@12345"

        # create account
        requests.post(
            "https://api.mail.tm/accounts",
            json={
                "address": email,
                "password": password
            }
        )

        # get token
        token_res = requests.post(
            "https://api.mail.tm/token",
            json={
                "address": email,
                "password": password
            }
        )

        token_data = token_res.json()

        token = token_data.get("token")

        if not token:
            bot.send_message(m.chat.id, "❌ Failed To Generate Token")
            return

        user_data[m.chat.id] = {
            "email": email,
            "token": token
        }

        bot.send_message(
            m.chat.id,
            f"📧 Your Temp Email:\n\n{email}\n\n"
            f"📥 Ready To Receive OTPs..."
        )

    except Exception as e:

        print("NEW EMAIL ERROR:", e)

        bot.send_message(
            m.chat.id,
            f"❌ Error Creating Email\n\n{e}"
        )


# ---------------- CHECK ----------------
@bot.message_handler(commands=['check'])
def check(m):

    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ पहले /new करो")
        return

    result = check_inbox(m.chat.id)

    if not result:
        bot.send_message(m.chat.id, "📭 No Email Yet")
        return

    bot.send_message(
        m.chat.id,
        f"📩 EMAIL RECEIVED\n\n"
        f"📌 Subject:\n{result['subject']}\n\n"
        f"📨 Message:\n{result['body'][:500]}"
    )


# ---------------- AUTO ----------------
@bot.message_handler(commands=['auto'])
def auto(m):

    if m.chat.id not in user_data:
        bot.send_message(m.chat.id, "❌ पहले /new करो")
        return

    if auto_running.get(m.chat.id):
        bot.send_message(m.chat.id, "⚠️ Auto already running")
        return

    bot.send_message(m.chat.id, "🔄 Auto OTP Checker Started")

    threading.Thread(
        target=auto_loop,
        args=(m.chat.id,)
    ).start()


# ---------------- STOP ----------------
@bot.message_handler(commands=['stop'])
def stop(m):

    auto_running[m.chat.id] = False

    bot.send_message(m.chat.id, "🛑 Stopping...")


# ---------------- RUN ----------------
print("✅ BOT RUNNING...")

bot.infinity_polling()
