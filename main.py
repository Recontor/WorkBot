import asyncio
import logging
from aiogram import Dispatcher, F
from aiogram.filters import Command

import config
import database
import handlers
import calculate
import admin_panel
from bot import bot
from handlers import BotStates
from admin_panel import RateStates

async def main():
    # Налаштування логування
    logging.basicConfig(level=logging.INFO)

    # Ініціалізація бази даних
    database.init_db()

    dp = Dispatcher()

    # --- 1. БАЗОВІ КОМАНДИ ТА НАВІГАЦІЯ ---
    dp.message.register(handlers.start_handler, Command("start"))
    dp.message.register(handlers.cmd_cancel, F.text.in_({"🏠 Меню", "❌ Відмінити та в меню", "❌ Відмінити"}))
    
    # --- 2. ГОЛОВНЕ МЕНЮ (TEXT BUTTONS) ---
    dp.message.register(calculate.operation_type_handler, F.text == "💱 Курс валют")
    dp.message.register(handlers.contacts_handler, F.text == "📞 Контакти")
    dp.message.register(handlers.help_handler, F.text == "ℹ️ Допомога")
    dp.message.register(handlers.tech_support_handler, F.text == "👨‍💻 Тех.підтримка")

    # --- 3. ІНЛАЙН КНОПКИ ТА КАЛЬКУЛЯТОР ---
    dp.callback_query.register(calculate.operation_type_handler, F.data == "mode_uah")
    dp.callback_query.register(calculate.cross_mode_handler, F.data == "mode_cross")
    dp.callback_query.register(calculate.select_currency_for_calc, F.data.in_({"calc_buy", "calc_sell", "calc_start"}))
    dp.callback_query.register(calculate.process_amount_entry, F.data.startswith("curr_"))
    dp.callback_query.register(handlers.cmd_cancel, F.data == "to_main")

    # Стан калькулятора (введення суми цифрами)
    dp.message.register(calculate.calculate_result_handler, BotStates.waiting_for_amount)

    # --- 4. ПОКРОКОВА ЗАЯВКА (FSM) ---
    dp.callback_query.register(calculate.start_free_request_callback, F.data == "start_free_request")
    
    # Реєстрація кроків опитування
    dp.message.register(calculate.process_req_phone, BotStates.waiting_for_req_phone)
    dp.message.register(calculate.process_req_currency, BotStates.waiting_for_req_currency)
    dp.message.register(calculate.process_req_amount, BotStates.waiting_for_req_amount)
    dp.message.register(calculate.process_req_final, BotStates.waiting_for_req_text)
    
    # --- 5. АДМІНІСТРАТОР ---
    dp.message.register(admin_panel.login_handler, Command("login"))
    
    # Керування курсами
    dp.callback_query.register(admin_panel.admin_rates_menu, F.data == "admin_rates_menu")
    dp.callback_query.register(admin_panel.edit_rate_start, F.data.startswith("edit_rate_"))
    dp.message.register(admin_panel.process_new_rate, RateStates.waiting_for_rate_value)
    
    # Крос-курси та Нотатки
    dp.callback_query.register(admin_panel.edit_cross_start, F.data == "edit_cross_text")
    dp.message.register(admin_panel.process_cross_text, RateStates.waiting_for_cross_text) # якщо функція реалізована
    dp.callback_query.register(admin_panel.admin_notes_handler, F.data == "admin_notes")
    dp.callback_query.register(admin_panel.edit_note_start, F.data == "edit_note_start")
    
    # Обробка заявок (Прийняти/Відхилити)
    dp.callback_query.register(admin_panel.handle_admin_request_choice, F.data.startswith("req_"))
    
    # Модерація та вихід
    dp.callback_query.register(admin_panel.toggle_turbo, F.data == "toggle_turbo")
    dp.callback_query.register(admin_panel.inspect_user_callback, F.data.startswith("inspect_"))
    dp.callback_query.register(admin_panel.process_ban, F.data.startswith("ban_"))
    dp.callback_query.register(admin_panel.admin_logout, F.data == "admin_logout")

# start bot
    try:
        print("✅ Бот успішно запущений!")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Бот зупинений.")