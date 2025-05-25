import telebot
from telebot import types
import os
import json
import uuid

TOKEN = "7987776972:AAFcUZ3Tf4GBeLl4mONaQiHV2MqDr3qz8r8"
ADMIN_ID = 465513095
DATA_FILE = "data.json"
FILES_DIR = "files"

bot = telebot.TeleBot(TOKEN)

os.makedirs(FILES_DIR, exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

def load_schemes():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_schemes(schemes):
    with open(DATA_FILE, "w") as f:
        json.dump(schemes, f)

@bot.message_handler(commands=['start'])
def start(message):
    schemes = load_schemes()
    markup = types.InlineKeyboardMarkup()
    for scheme in schemes:
        markup.add(types.InlineKeyboardButton(f"{scheme['title']} — {scheme['price']}₽", callback_data=f"buy_{scheme['id']}"))
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите схему:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_buy(call):
    scheme_id = call.data.split("_")[1]
    schemes = load_schemes()
    for scheme in schemes:
        if scheme["id"] == scheme_id:
            msg = f"📄 <b>{scheme['title']}</b>\n\n{scheme['desc']}\n\n💰 Цена: {scheme['price']}₽\n\n❗Оплатите по ссылке: https://www.donationalerts.com/r/danil222711\nПосле оплаты пришлите скриншот сюда."
            bot.send_message(call.message.chat.id, msg, parse_mode='HTML')
            return

@bot.message_handler(content_types=['photo', 'document'])
def handle_payment(message):
    if message.from_user.username:
        user = f"@{message.from_user.username}"
    else:
        user = f"id:{message.from_user.id}"
    bot.send_message(ADMIN_ID, f"🧾 Скрин оплаты от {user}")
    bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

@bot.message_handler(commands=['выдать'])
def issue_scheme(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.strip().split()
    if len(parts) != 3:
        bot.reply_to(message, "Используй: /выдать @username scheme_id")
        return
    username, scheme_id = parts[1], parts[2]
    schemes = load_schemes()
    for scheme in schemes:
        if scheme["id"] == scheme_id:
            path = os.path.join(FILES_DIR, scheme["file"])
            with open(path, "rb") as f:
                bot.send_document(username, f)
            return

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить схему", "📂 Список схем", "❌ Удалить схему")
    bot.send_message(message.chat.id, "Панель админа:", reply_markup=markup)

admin_state = {}

@bot.message_handler(func=lambda msg: msg.text == "➕ Добавить схему")
def add_title_step(message):
    admin_state[message.chat.id] = {"step": "title"}
    bot.send_message(message.chat.id, "Введите название схемы:")

@bot.message_handler(func=lambda msg: admin_state.get(msg.chat.id, {}).get("step") == "title")
def add_desc_step(message):
    admin_state[message.chat.id]["title"] = message.text
    admin_state[message.chat.id]["step"] = "desc"
    bot.send_message(message.chat.id, "Введите описание схемы:")

@bot.message_handler(func=lambda msg: admin_state.get(msg.chat.id, {}).get("step") == "desc")
def add_price_step(message):
    admin_state[message.chat.id]["desc"] = message.text
    admin_state[message.chat.id]["step"] = "price"
    bot.send_message(message.chat.id, "Введите цену в рублях:")

@bot.message_handler(func=lambda msg: admin_state.get(msg.chat.id, {}).get("step") == "price")
def add_file_step(message):
    try:
        price = int(message.text)
        admin_state[message.chat.id]["price"] = price
        admin_state[message.chat.id]["step"] = "file"
        bot.send_message(message.chat.id, "Теперь отправьте файл схемы (PDF, ZIP и т.д.):")
    except ValueError:
        bot.send_message(message.chat.id, "Цена должна быть числом.")

@bot.message_handler(content_types=['document'], func=lambda msg: admin_state.get(msg.chat.id, {}).get("step") == "file")
def save_scheme(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{unique_id}_{message.document.file_name}"
    filepath = os.path.join(FILES_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(downloaded_file)

    data = admin_state.pop(message.chat.id)
    scheme = {
        "id": unique_id,
        "title": data["title"],
        "desc": data["desc"],
        "price": data["price"],
        "file": filename
    }
    schemes = load_schemes()
    schemes.append(scheme)
    save_schemes(schemes)
    bot.send_message(message.chat.id, "✅ Схема добавлена!")

@bot.message_handler(func=lambda msg: msg.text == "📂 Список схем")
def list_schemes(message):
    schemes = load_schemes()
    text = "📄 Список схем:\n"
    for s in schemes:
        text += f"{s['id']}: {s['title']} ({s['price']}₽)\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda msg: msg.text == "❌ Удалить схему")
def ask_id_to_delete(message):
    schemes = load_schemes()
    text = "❌ Введите ID схемы для удаления:\n"
    for s in schemes:
        text += f"{s['id']}: {s['title']}\n"
    admin_state[message.chat.id] = {"step": "delete"}
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda msg: admin_state.get(msg.chat.id, {}).get("step") == "delete")
def delete_scheme(message):
    scheme_id = message.text.strip()
    schemes = load_schemes()
    schemes = [s for s in schemes if s["id"] != scheme_id]
    save_schemes(schemes)
    admin_state.pop(message.chat.id)
    bot.send_message(message.chat.id, "✅ Схема удалена (если была).")

print("Бот запущен")
bot.polling()
