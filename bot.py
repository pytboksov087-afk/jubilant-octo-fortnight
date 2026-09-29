import telebot
from telebot import types
import json
import os
import random
import string
import threading
import time
import calendar
from datetime import datetime


TOKEN = "8998770154:AAFMTFETqt321kW-mQQQuY3wiy5S8gLn9d4"
DB_FILE = "pairs.json"


def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"pairs": {}, "users": {}, "reminders": [], "anniversaries": {}}


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


db = load_db()
if "reminders" not in db:
    db["reminders"] = []
if "anniversaries" not in db:
    db["anniversaries"] = {}


bot = telebot.TeleBot(TOKEN)


def main_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Скучаю 🥺"))
    markup.add(types.KeyboardButton("Хочу 🎁"))
    markup.add(types.KeyboardButton("Напоминание ⏰"))
    markup.add(types.KeyboardButton("Годовщина 💍"))
    return markup


def start_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Создать пару 💞"))
    markup.add(types.KeyboardButton("Ввести код 🔑"))
    return markup


def cancel_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Отмена ❌"))
    return markup


def gen_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


def add_months(d, months):
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)


def plural(n, one, few, many):
    n = abs(n) % 100
    if 11 <= n <= 19:
        return many
    n = n % 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def format_duration(months):
    if months <= 0:
        return "меньше месяца"
    y = months // 12
    m = months % 12
    parts = []
    if y > 0:
        parts.append(str(y) + " " + plural(y, "год", "года", "лет"))
    if m > 0:
        parts.append(str(m) + " " + plural(m, "месяц", "месяца", "месяцев"))
    return " ".join(parts)


def get_partner(uid):
    uid = str(uid)
    if uid not in db["users"]:
        return None
    code = db["users"][uid]
    pair = db["pairs"].get(code)
    if not pair:
        return None
    return pair[1] if pair[0] == uid else pair[0]


@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.chat.id)
    if uid in db["users"]:
        bot.send_message(uid, "Ты уже в паре 💞 Жми кнопку!", reply_markup=main_kb())
        return
    bot.send_message(uid, "Привет! Это бот для двоих 💌\n\nОдин создаёт пару и получает код.\nВторой вводит код — и вы связаны.", reply_markup=start_kb())


@bot.message_handler(func=lambda m: m.text == "Создать пару 💞")
def create_pair(message):
    uid = str(message.chat.id)
    if uid in db["users"]:
        bot.send_message(uid, "Ты уже в паре 💞", reply_markup=main_kb())
        return
    code = gen_code()
    while code in db["pairs"]:
        code = gen_code()
    db["pairs"][code] = [uid, None]
    db["users"][uid] = code
    save_db(db)
    bot.send_message(uid, "Пара создана! 💞\n\nТвой код: " + code + "\n\nПередай его второй половинке. Пусть нажмёт /start → «Ввести код 🔑».", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "Ввести код 🔑")
def ask_code(message):
    uid = str(message.chat.id)
    if uid in db["users"]:
        bot.send_message(uid, "Ты уже в паре 💞", reply_markup=main_kb())
        return
    msg = bot.send_message(uid, "Введи код приглашения (4 символа):", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, join_pair)


def join_pair(message):
    uid = str(message.chat.id)
    if message.text == "Отмена ❌":
        bot.send_message(uid, "Ок, отменил.", reply_markup=start_kb())
        return
    code = message.text.strip().upper()
    if code not in db["pairs"]:
        bot.send_message(uid, "Такого кода нет 🤔 Попробуй ещё раз: /start", reply_markup=start_kb())
        return
    pair = db["pairs"][code]
    if pair[1] is not None:
        bot.send_message(uid, "Этот код уже использован 😔", reply_markup=start_kb())
        return
    if pair[0] == uid:
        bot.send_message(uid, "Это твой же код 😄 Передай его партнёру.", reply_markup=start_kb())
        return
    pair[1] = uid
    db["users"][uid] = code
    save_db(db)
    bot.send_message(uid, "Вы связаны! 💞 Жми кнопку.", reply_markup=main_kb())
    bot.send_message(pair[0], "Твоя половинка подключилась! 💞", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "Скучаю 🥺")
def miss(message):
    uid = str(message.chat.id)
    if uid not in db["users"]:
        bot.send_message(uid, "Сначала создай пару: /start")
        return
    partner = get_partner(uid)
    if partner is None:
        bot.send_message(uid, "Партнёр ещё не подключился. Жди 💌")
        return
    bot.send_message(partner, "Тебе передали: Скучаю 🥺")
    bot.send_message(uid, "Передал ✅")


@bot.message_handler(func=lambda m: m.text == "Хочу 🎁")
def ask_want(message):
    uid = str(message.chat.id)
    if uid not in db["users"]:
        bot.send_message(uid, "Сначала создай пару: /start")
        return
    partner = get_partner(uid)
    if partner is None:
        bot.send_message(uid, "Партнёр ещё не подключился. Жди 💌")
        return
    msg = bot.send_message(uid, "Что хочешь? Напиши:", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, send_want)


def send_want(message):
    uid = str(message.chat.id)
    if message.text == "Отмена ❌":
        bot.send_message(uid, "Ок, отменил.", reply_markup=main_kb())
        return
    text = message.text.strip()
    if len(text) > 200:
        bot.send_message(uid, "Слишком длинно, давай покороче.", reply_markup=main_kb())
        return
    partner = get_partner(uid)
    if partner is None:
        bot.send_message(uid, "Партнёр не найден.", reply_markup=main_kb())
        return
    bot.send_message(partner, "🎁 Партнёр хочет: " + text)
    bot.send_message(uid, "Передал ✅", reply_markup=main_kb())


@bot.message_handler(func=lambda m: m.text == "Напоминание ⏰")
def ask_reminder(message):
    uid = str(message.chat.id)
    if uid not in db["users"]:
        bot.send_message(uid, "Сначала создай пару: /start")
        return
    partner = get_partner(uid)
    if partner is None:
        bot.send_message(uid, "Партнёр ещё не подключился. Жди 💌")
        return
    msg = bot.send_message(uid, "О чём напомнить? Напиши текст:", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, ask_reminder_time)


def ask_reminder_time(message):
    uid = str(message.chat.id)
    if message.text == "Отмена ❌":
        bot.send_message(uid, "Ок, отменил.", reply_markup=main_kb())
        return
    text = message.text.strip()
    if len(text) > 200:
        bot.send_message(uid, "Слишком длинно, давай покороче (до 200 символов).")
        return
    msg = bot.send_message(uid, "Когда напомнить?\nФормат: ДД.ММ.ГГГГ ЧЧ:ММ\nНапример: 01.10.2026 15:30", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, save_reminder, text)


def save_reminder(message, text):
    uid = str(message.chat.id)
    if message.text == "Отмена ❌":
        bot.send_message(uid, "Ок, отменил.", reply_markup=main_kb())
        return
    raw = message.text.strip()
    try:
        dt = datetime.strptime(raw, "%d.%m.%Y %H:%M")
    except ValueError:
        bot.send_message(uid, "Не понял дату 🤔 Нужно так: 01.10.2026 15:30\nПопробуй ещё раз — жми «Напоминание ⏰».", reply_markup=main_kb())
        return
    if dt <= datetime.now():
        bot.send_message(uid, "Это время уже прошло ⏳ Жми «Напоминание ⏰» и введи будущее.", reply_markup=main_kb())
        return
    code = db["users"][uid]
    partner = get_partner(uid)
    reminder = {
        "code": code,
        "text": text,
        "time": dt.strftime("%Y-%m-%d %H:%M"),
        "created_by": uid
    }
    db["reminders"].append(reminder)
    save_db(db)
    pretty = dt.strftime("%d.%m.%Y %H:%M")
    bot.send_message(uid, "Записал ⏰ Напомню " + pretty + "\nТекст: " + text, reply_markup=main_kb())
    if partner:
        bot.send_message(partner, "Партнёр добавил напоминание ⏰\nКогда: " + pretty + "\nО чём: " + text)


@bot.message_handler(func=lambda m: m.text == "Годовщина 💍")
def ask_anniv(message):
    uid = str(message.chat.id)
    if uid not in db["users"]:
        bot.send_message(uid, "Сначала создай пару: /start")
        return
    partner = get_partner(uid)
    if partner is None:
        bot.send_message(uid, "Партнёр ещё не подключился. Жди 💌")
        return
    msg = bot.send_message(uid, "Когда вы начали встречаться?\nФормат: ДД.ММ.ГГГГ\nНапример: 15.01.2026", reply_markup=cancel_kb())
    bot.register_next_step_handler(msg, save_anniv)


def save_anniv(message):
    uid = str(message.chat.id)
    if message.text == "Отмена ❌":
        bot.send_message(uid, "Ок, отменил.", reply_markup=main_kb())
        return
    raw = message.text.strip()
    try:
        d = datetime.strptime(raw, "%d.%m.%Y")
    except ValueError:
        bot.send_message(uid, "Не понял дату 🤔 Нужно так: 15.01.2026\nПопробуй ещё — жми «Годовщина 💍».", reply_markup=main_kb())
        return
    if d > datetime.now():
        bot.send_message(uid, "Эта дата в будущем 🤔 Введи прошедшую.", reply_markup=main_kb())
        return
    code = db["users"][uid]
    partner = get_partner(uid)
    db["anniversaries"][code] = {"date": d.strftime("%Y-%m-%d"), "sent": []}
    save_db(db)
    pretty = d.strftime("%d.%m.%Y")
    bot.send_message(uid, "Запомнил 💍 Дата начала: " + pretty + "\nБуду напоминать каждый месяц.", reply_markup=main_kb())
    if partner:
        bot.send_message(partner, "💍 Партнёр установил дату начала отношений: " + pretty)


@bot.message_handler(commands=['together'])
def together(message):
    uid = str(message.chat.id)
    if uid not in db["users"]:
        bot.send_message(uid, "Сначала создай пару: /start")
        return
    code = db["users"][uid]
    data = db["anniversaries"].get(code)
    if not data:
        bot.send_message(uid, "Дата начала не установлена. Жми «Годовщина 💍».", reply_markup=main_kb())
        return
    start = datetime.strptime(data["date"], "%Y-%m-%d")
    today = datetime.now()
    days = (today.date() - start.date()).days
    months = (today.year - start.year) * 12 + (today.month - start.month)
    if add_months(start, months).date() > today.date():
        months -= 1
    label = format_duration(months) if months > 0 else "меньше месяца"
    next_month = months + 1
    next_date = add_months(start, next_month)
    delta = (next_date.date() - today.date()).days
    text = "💞 Вы вместе: " + str(days) + " дней"
    text += "\nЭто " + label
    text += "\nСледующая дата: " + next_date.strftime("%d.%m.%Y") + " (" + format_duration(next_month) + ")"
    text += "\nОсталось: " + str(delta) + " дней"
    bot.send_message(uid, text, reply_markup=main_kb())


def reminder_worker():
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            fired = []
            for r in db["reminders"]:
                if r["time"] == now:
                    fired.append(r)
            for r in fired:
                db["reminders"].remove(r)
                pair = db["pairs"].get(r["code"])
                if not pair:
                    continue
                pretty = datetime.strptime(r["time"], "%Y-%m-%d %H:%M").strftime("%d.%m.%Y %H:%M")
                for who in pair:
                    if who:
                        try:
                            bot.send_message(who, "⏰ Напоминание!\n" + r["text"] + "\n(" + pretty + ")")
                        except Exception:
                            pass
            if fired:
                save_db(db)
        except Exception as e:
            print("Reminder error:", e)
        time.sleep(30)


def anniversary_worker():
    while True:
        try:
            today = datetime.now().date()
            changed = False
            for code, data in list(db["anniversaries"].items()):
                start = datetime.strptime(data["date"], "%Y-%m-%d")
                pair = db["pairs"].get(code)
                if not pair:
                    continue
                months = (today.year - start.year) * 12 + (today.month - start.month)
                if months <= 0:
                    continue
                target = add_months(start, months).date()
                if target != today:
                    continue
                key = "m" + str(months)
                if key in data.get("sent", []):
                    continue
                label = format_duration(months)
                for who in pair:
                    if who:
                        try:
                            bot.send_message(who, "🎉 Сегодня " + label + " как вы вместе! 💞")
                        except Exception:
                            pass
                data.setdefault("sent", []).append(key)
                changed = True
            if changed:
                save_db(db)
        except Exception as e:
            print("Anniversary error:", e)
        time.sleep(3600)


threading.Thread(target=reminder_worker, daemon=True).start()
threading.Thread(target=anniversary_worker, daemon=True).start()


@bot.message_handler(commands=['help'])
def help_cmd(message):
    uid = str(message.chat.id)
    text = (
        "📋 Команды бота:\n\n"
        "/start — начать / регистрация\n"
        "/together — сколько вы вместе\n"
        "/help — этот список\n"
        "/reset — выйти из пары\n\n"
        "🔘 Кнопки внизу экрана:\n"
        "• Скучаю 🥺 — передать партнёру\n"
        "• Хочу 🎁 — сказать, что хочешь\n"
        "• Напоминание ⏰ — поставить напоминание\n"
        "• Годовщина 💍 — задать дату начала"
    )
    bot.send_message(uid, text, reply_markup=main_kb())


@bot.message_handler(commands=['reset'])
def reset(message):
    uid = str(message.chat.id)
    if uid in db["users"]:
        code = db["users"].pop(uid)
        if code in db["pairs"]:
            pair = db["pairs"][code]
            if pair[0] == uid:
                db["pairs"].pop(code)
                db["anniversaries"].pop(code, None)
                if pair[1]:
                    db["users"].pop(pair[1], None)
            else:
                pair[1] = None
    save_db(db)
    bot.send_message(uid, "Готово. Начни заново: /start", reply_markup=start_kb())


bot.infinity_polling()