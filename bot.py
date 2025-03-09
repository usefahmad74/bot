import telebot
from telebot import types
import sqlite3

# توکن ربات
TOKEN = "8034712658:AAHeaIjRvj2z08-pHgHqqqEE6dxVB79Plk0"
# آیدی ادمین (خودت)
ADMIN_ID = 7836825805
# کانال اعتمادسازی
TRUST_CHANNEL = "@HashPayTron"

bot = telebot.TeleBot(TOKEN)

# دیتابیس
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, lang TEXT, balance REAL DEFAULT 0, wallet TEXT)''')
conn.commit()

def save_user(user_id, lang=None, balance=None, wallet=None):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    if lang:
        cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    if balance is not None:
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (balance, user_id))
    if wallet:
        cursor.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (wallet, user_id))
    conn.commit()

def get_user(user_id):
    cursor.execute("SELECT lang, balance, wallet FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return {"lang": result[0], "balance": result[1], "wallet": result[2]}
    return {"lang": None, "balance": 0, "wallet": None}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id = int(args[1].split("_")[1])
        if user_id != referrer_id:
            user_data = get_user(referrer_id)
            new_balance = user_data["balance"] + 0.25
            save_user(referrer_id, balance=new_balance)
            bot.send_message(referrer_id, "یک زیرمجموعه جدید اضافه شد! موجودی: {:.2f} TRX".format(new_balance))

    markup = types.InlineKeyboardMarkup()
    btn_en = types.InlineKeyboardButton("English", callback_data="lang_en")
    btn_fa = types.InlineKeyboardButton("فارسی", callback_data="lang_fa")
    markup.add(btn_en, btn_fa)
    bot.send_message(user_id, "زبان را انتخاب کنید\nChoose your language", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def handle_language(call):
    user_id = call.from_user.id
    lang = "en" if call.data == "lang_en" else "fa"
    save_user(user_id, lang=lang)
    bot.answer_callback_query(call.id)
    check_channels(call.message, lang)

def check_channels(message, lang):
    user_id = message.chat.id
    channels = ["@HashPayTron", "@Drops1Drop", "@TonWinNews"]  # کانال‌های اجباری
    not_joined = []

    for channel in channels:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ["member", "administrator", "creator"]:
                not_joined.append(channel)
        except:
            not_joined.append(channel)

    if not_joined:
        markup = types.InlineKeyboardMarkup()
        for channel in not_joined:
            markup.add(types.InlineKeyboardButton(f"Join {channel}", url=f"https://t.me/{channel[1:]}"))
        markup.add(types.InlineKeyboardButton("تأیید" if lang == "fa" else "Confirm", callback_data="check_again"))
        bot.send_message(user_id, "لطفاً در کانال‌های زیر عضو شوید:" if lang == "fa" else "Please join the channels below:", reply_markup=markup)
    else:
        show_main_menu(message, lang)

@bot.callback_query_handler(func=lambda call: call.data == "check_again")
def recheck_channels(call):
    user_data = get_user(call.from_user.id)
    check_channels(call.message, user_data["lang"])

def show_main_menu(message, lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = {
        "fa": ["💰 موجودی حساب", "📩 رفرال‌گیری", "💸 برداشت", "📞 پشتیبانی"],
        "en": ["💰 Balance", "📩 Referral", "💸 Withdraw", "📞 Support"]
    }
    for btn in btns[lang]:
        markup.add(types.KeyboardButton(btn))
    bot.send_message(message.chat.id, "منوی اصلی" if lang == "fa" else "Main Menu", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["💰 موجودی حساب", "💰 Balance", "📩 رفرال‌گیری", "📩 Referral", "💸 برداشت", "💸 Withdraw", "📞 پشتیبانی", "📞 Support"])
def handle_menu(message):
    user_id = message.chat.id
    user_data = get_user(user_id)
    lang = user_data["lang"]
    text = message.text

    if text in ["💰 موجودی حساب", "💰 Balance"]:
        bot.send_message(user_id, f"موجودی شما: {user_data['balance']:.2f} TRX")
    
    elif text in ["📩 رفرال‌گیری", "📩 Referral"]:
        ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{user_id}"
        bot.send_message(user_id, f"لینک رفرال شما:\n{ref_link}" if lang == "fa" else f"Your referral link:\n{ref_link}")
    
    elif text in ["💸 برداشت", "💸 Withdraw"]:
        if user_data["balance"] < 3:
            bot.send_message(user_id, "حداقل موجودی برای برداشت ۳ ترون است" if lang == "fa" else "Minimum balance for withdrawal is 3 TRX")
        else:
            bot.send_message(user_id, "آدرس کیف پول ترون خود را ارسال کنید" if lang == "fa" else "Send your TRON wallet address")
            bot.register_next_step_handler(message, process_wallet)
    
    elif text in ["📞 پشتیبانی", "📞 Support"]:
        bot.send_message(user_id, "پیام خود را بنویسید" if lang == "fa" else "Write your message")
        bot.register_next_step_handler(message, forward_to_admin)

def process_wallet(message):
    user_id = message.chat.id
    wallet = message.text
    user_data = get_user(user_id)
    lang = user_data["lang"]
    amount = 3

    if user_data["balance"] >= 3:
        new_balance = user_data["balance"] - amount
        save_user(user_id, balance=new_balance, wallet=wallet)
        bot.send_message(user_id, "در ساعات آینده واریز انجام می‌شود" if lang == "fa" else "Payment will be processed in the coming hours")
        bot.send_message(ADMIN_ID, f"درخواست برداشت:\nکاربر: {user_id}\nمقدار: {amount} TRX\nکیف پول: {wallet}")
    else:
        bot.send_message(user_id, "موجودی کافی نیست" if lang == "fa" else "Insufficient balance")

def forward_to_admin(message):
    user_id = message.chat.id
    bot.forward_message(ADMIN_ID, user_id, message.message_id)
    bot.send_message(user_id, "پیام شما ارسال شد" if lang == "fa" else "Your message has been sent")

@bot.message_handler(func=lambda msg: msg.reply_to_message and msg.chat.id == ADMIN_ID)
def reply_to_user(message):
    user_id = message.reply_to_message.forward_from.id
    bot.send_message(user_id, message.text)
    wallet = get_user(user_id)["wallet"]
    tx_hash = "YOUR_TX_HASH_HERE"  # هش تراکنش رو دستی وارد کن
    proof = f"واریز انجام شد\nآیدی: {str(user_id)[:5]}...\nکیف پول: ...{wallet[-5:]}\nهش: {tx_hash}"
    bot.send_message(TRUST_CHANNEL, proof)

bot.polling()