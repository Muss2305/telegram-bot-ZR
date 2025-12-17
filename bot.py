from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import gspread
from datetime import datetime, timedelta
import json
import os
from google.oauth2.service_account import Credentials

# ---------- TOKEN ----------
TOKEN = os.getenv("8259750529:AAEEzVyMsTlvNBM6dZ_L0E22ECTV2GQw_po")  # ← в Railway Variables
ADMIN_ID = 2032417511

# ---------- GOOGLE SHEETS ----------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets ",
    "https://www.googleapis.com/auth/drive "
]

creds = Credentials.from_service_account_info(
    json.loads(os.getenv("clients-481219-2f486a72fb64.json")),
    scopes=SCOPES
)

gc = gspread.authorize(creds)
sheet_clients = gc.open("Клиенты").worksheet("Клиенты")
sheet_blocks = gc.open("Клиенты").worksheet("Блокировки")
sheet_archive = gc.open("Клиенты").worksheet("Архив")

# ---------- НАСТРОЙКИ ----------
ALL_TIMES = ["10:00", "10:40", "11:20", "12:20", "13:00", "13:40", "14:20", "15:00", "15:40"]

# ---------- МЕНЮ ----------
main_menu = [
    [InlineKeyboardButton("Вопросы о техниках", callback_data="bot")],
    [InlineKeyboardButton("Запись на процедуру", callback_data="barbing")],
    [InlineKeyboardButton("Кого принимает Зульфия на процедуру", callback_data="procedura")]
]

bot_questions = [
    [InlineKeyboardButton("Чем помогают техники", callback_data="bot_life")],
    [InlineKeyboardButton("Сколько сеансов нужно для оздоровления", callback_data="bot_life3")],
    [InlineKeyboardButton("Какие техники используются", callback_data="bot_life4")],
    [InlineKeyboardButton("Назад", callback_data="back_main")]
]

barbing = [
    [InlineKeyboardButton("Где Зульфия работает", callback_data="say_work")],
    [InlineKeyboardButton("Сколько стоит процедура", callback_data="say_tsena")],
    [InlineKeyboardButton("Хочу записаться", callback_data="say_zapis")],
    [InlineKeyboardButton("Назад", callback_data="back_main")]
]

bot_life4 = [
    [InlineKeyboardButton("Остеопатия", callback_data="osteo")],
    [InlineKeyboardButton("Правка пупа", callback_data="pupok")],
    [InlineKeyboardButton("Висцеральная техника", callback_data="visc")],
    [InlineKeyboardButton("Диафрагмальная техника", callback_data="diafr")],
    [InlineKeyboardButton("Мануальная техника", callback_data="manual")],
    [InlineKeyboardButton("Назад", callback_data="back_main")]
]

# ---------- ДАТЫ ----------
def get_date_keyboard(days=30):
    kb, row = [], []
    today = datetime.now()
    for i in range(days):
        d = today + timedelta(days=i)
        row.append(
            InlineKeyboardButton(
                d.strftime("%d.%m.%Y"),
                callback_data=f"date_{d.strftime('%Y-%m-%d')}"
            )
        )
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return InlineKeyboardMarkup(kb)

# ---------- ВРЕМЯ ----------
def get_free_times(date):
    clients = sheet_clients.get_all_values()[1:]
    blocks = sheet_blocks.get_all_values()[1:]
    busy = [r[3] for r in clients if r[0] == date]
    blocked = [r[1] for r in blocks if r[0] == date]
    return [t for t in ALL_TIMES if t not in busy and t not in blocked]

# ---------- АРХИВ ----------
def archive_old():
    today = datetime.now().date()
    rows = sheet_clients.get_all_values()[1:]
    for idx, r in enumerate(rows, start=2):
        try:
            if datetime.strptime(r[0], "%Y-%m-%d").date() < today:
                sheet_archive.append_row(
                    [r[0], r[1], r[2], r[3], datetime.now().strftime("%Y-%m-%d %H:%M")]
                )
                sheet_clients.delete_row(idx)
        except:
            continue

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    archive_old()
    context.user_data.clear()
    await update.message.reply_text(
        "Ассаляму алейкум, какой вопрос у вас?",
        reply_markup=InlineKeyboardMarkup(main_menu)
    )

# ---------- ADMIN ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к админ-панели.")
        return

    rows = sheet_clients.get_all_values()[1:]
    if not rows:
        await update.message.reply_text("📭 Нет активных записей.")
        return

    keyboard = []
    for r in rows:
        keyboard.append([
            InlineKeyboardButton(
                f"{r[0]} {r[3]} — {r[1]}",
                callback_data=f"admin_del_{r[0]}_{r[3]}_{r[2]}"
            )
        ])

    await update.message.reply_text(
        "📋 Активные записи:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- CALLBACK ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "bot":
        await query.message.edit_text("Вопросы по техникам:", reply_markup=InlineKeyboardMarkup(bot_questions))

    elif data == "barbing":
        await query.message.edit_text("Вопросы о записи на процедуру:", reply_markup=InlineKeyboardMarkup(barbing))

    elif data == "say_zapis":
        context.user_data.clear()
        context.user_data["step"] = "name"
        await query.message.edit_text("Введите имя и фамилию:")

    elif data.startswith("date_"):
        date = data.replace("date_", "")
        context.user_data["date"] = date
        free = get_free_times(date)
        if not free:
            await query.message.edit_text(
                "❌ На эту дату все время занято. Выберите другую дату.",
                reply_markup=get_date_keyboard()
            )
        else:
            kb = [[InlineKeyboardButton(t, callback_data=f"time_{t}")] for t in free]
            await query.message.edit_text(
                f"Дата: {date}\nВыберите свободное время:",
                reply_markup=InlineKeyboardMarkup(kb)
            )

    elif data.startswith("time_"):
        time = data.replace("time_", "")
        name = context.user_data.get("name")
        phone = context.user_data.get("phone")
        date = context.user_data.get("date")

        sheet_clients.append_row([date, name, phone, time])

        await context.bot.send_message(
            ADMIN_ID,
            f"📥 Новая запись\n\n👤 {name}\n📞 {phone}\n📅 {date}\n⏰ {time}"
        )

        await query.message.edit_text(
            "✅ Запись подтверждена.\nЕсли есть еще вопросы нажмите /start"
        )
        context.user_data.clear()

    elif data == "procedura":
        await query.message.edit_text(
            "Женщин любого возраста и мальчиков до 13 лет.\nЕсли есть еще вопросы нажмите: /start"
        )

    elif data == "back_main":
        await query.message.edit_text(
            "Ассаляму алейкум, какой вопрос у вас?",
            reply_markup=InlineKeyboardMarkup(main_menu)
        )

# ---------- TEXT ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    if step == "name":
        context.user_data["name"] = update.message.text
        context.user_data["step"] = "phone"
        await update.message.reply_text("Введите номер телефона:")
    elif step == "phone":
        context.user_data["phone"] = update.message.text
        context.user_data["step"] = "date"
        await update.message.reply_text("Выберите дату:", reply_markup=get_date_keyboard())

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()