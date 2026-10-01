import asyncio
import time
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup

import database
import config
from bot import bot
from handlers import BotStates, main_menu

# Спеціальні стани для адмін-панелі
class RateStates(StatesGroup):
    waiting_for_rate_value = State()
    waiting_for_cross_text = State()
    waiting_for_admin_note = State()

def get_admin_kb():
    """Основне меню для модераторів"""
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📈 Оновити курси", callback_data="admin_rates_menu"))
    kb.row(types.InlineKeyboardButton(text="📋 Нотатки", callback_data="admin_notes"))
    kb.row(types.InlineKeyboardButton(text="📢 Розсилка", callback_data="admin_broadcast"))
    kb.row(types.InlineKeyboardButton(text="🔒 Вихід", callback_data="admin_logout"))
    return kb.as_markup()

def get_owner_kb():
    """Розширене меню для власника (Owner)"""
    kb = InlineKeyboardBuilder()
    turbo = database.get_setting('turbo_mode')
    turbo_text = "🚀 ТУРБО: ON" if turbo == 'on' else "🚀 ТУРБО: OFF"
    
    kb.row(types.InlineKeyboardButton(text=turbo_text, callback_data="toggle_turbo"))
    kb.row(types.InlineKeyboardButton(text="📈 Керування курсами", callback_data="admin_rates_menu"))
    kb.row(types.InlineKeyboardButton(text="📋 Нотатки", callback_data="admin_notes"))
    kb.row(types.InlineKeyboardButton(text="🔒 Вихід", callback_data="admin_logout"))
    return kb.as_markup()

async def login_handler(message: types.Message, state: FSMContext):
    """Авторизація адміна"""
    user_id = message.from_user.id
    is_owner = (user_id == config.SUPER_ADMIN_ID)
    
    if not is_owner and user_id not in config.ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("🔑 Введіть: `/login пароль`", parse_mode="Markdown")
        return

    if args[1] == config.ADMIN_PASSWORD:
        database.register_admin_session(user_id, message.from_user.username)
        await state.set_state(BotStates.admin_active)
        
        greeting = "👑 ВІТАЄМО, ВЛАСНИКУ!" if is_owner else "⚙️ АДМІН-ПАНЕЛЬ АКТИВОВАНА"
        kb = get_owner_kb() if is_owner else get_admin_kb()
        await message.answer(greeting, reply_markup=kb)
    else:
        await message.answer("❌ Невірний пароль.")

async def toggle_turbo(callback: types.CallbackQuery):
    """Перемикання турбо-режиму (тільки власник)"""
    if callback.from_user.id != config.SUPER_ADMIN_ID:
        await callback.answer("Тільки для Owner", show_alert=True)
        return
    current = database.get_setting('turbo_mode')
    new_status = 'on' if current == 'off' else 'off'
    database.set_turbo_mode(new_status)
    await callback.message.edit_reply_markup(reply_markup=get_owner_kb())
    await callback.answer(f"Турбо-режим: {new_status.upper()}", show_alert=True)
    
async def admin_rates_menu(callback: types.CallbackQuery):
    """Вибір валюти для зміни курсу"""
    builder = InlineKeyboardBuilder()
    currencies = [
        ("USD_NEW", "🇺🇸 USD Новий"), ("USD_OLD", "🇺🇸 USD Білий"),
        ("EUR", "🇪🇺 EURO"), ("PLN", "🇵🇱 PLN"), ("GBP", "🇬🇧 GBP"),
        ("CHF", "🇨🇭 CHF"), ("CAD", "🇨🇦 CAD"), ("CZK", "🇨🇿 CZK"), ("SEK", "🇸🇪 SEK")
    ]
    for code, name in currencies:
        builder.add(types.InlineKeyboardButton(text=f"Курс {name}", callback_data=f"edit_rate_{code}"))
    
    builder.adjust(2)
    builder.row(types.InlineKeyboardButton(text="🔄 Текст Крос-курсів", callback_data="edit_cross_text"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_home"))
    await callback.message.edit_text("Оберіть валюту для оновлення:", reply_markup=builder.as_markup())

async def edit_rate_start(callback: types.CallbackQuery, state: FSMContext):
    """Запит нових значень курсу"""
    currency = callback.data.replace("edit_rate_", "")
    await state.update_data(edit_curr=currency)
    await state.set_state(RateStates.waiting_for_rate_value)
    
    # Використовуємо HTML (<b> замість ** та <code> замість `)
    await callback.message.answer(
        f"📈 Введіть 4 числа для <b>{currency}</b> через пробіл:\n"
        f"<code>Купівля Продаж Куп_Опт Прод_Опт</code>", 
        parse_mode="HTML"
    )
    await callback.answer()
async def process_new_rate(message: types.Message, state: FSMContext):
    """Збереження курсу в БД та вивід меню дій"""
    try:
        data = await state.get_data()
        parts = message.text.replace(",", ".").split()
        if len(parts) != 4: 
            raise ValueError
        buy, sell, buy_opt, sell_opt = map(float, parts)
        database.set_rate(data['edit_curr'], buy, sell, buy_opt, sell_opt)
        
        # Визначаємо меню залежно від прав (Owner / Admin)
        is_owner = (message.from_user.id == config.SUPER_ADMIN_ID)
        kb = get_owner_kb() if is_owner else get_admin_kb()

        await message.answer(
            f"✅ Курс <b>{data['edit_curr']}</b> успішно оновлено!\n\nОберіть наступну дію:", 
            reply_markup=kb,
            parse_mode="HTML"
        )
        await state.set_state(BotStates.admin_active)
    except Exception:
        await message.answer("❌ Помилка! Введіть 4 числа через пробіл (напр: 41.2 41.8 41.4 41.6)")

async def process_cross_text(message: types.Message, state: FSMContext):
    """Збереження нового тексту крос-курсів та вивід меню"""
    new_text = message.text
    database.set_setting('cross_rates_info', new_text)
    
    is_owner = (message.from_user.id == config.SUPER_ADMIN_ID)
    kb = get_owner_kb() if is_owner else get_admin_kb()

    await message.answer(
        f"✅ <b>Текст крос-курсів оновлено!</b>\n\nТепер у розділі буде:\n<code>{new_text}</code>\n\nОберіть наступну дію:", 
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(BotStates.admin_active)
    
async def admin_notes_handler(callback: types.CallbackQuery):
    """Блокнот адміна"""
    note = database.get_note()
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📝 Редагувати", callback_data="edit_note_start"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_home"))
    await callback.message.edit_text(f"📋 **НОТАТКИ:**\n\n{note}", reply_markup=kb.as_markup(), parse_mode="Markdown")

async def edit_note_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RateStates.waiting_for_admin_note)
    await callback.message.answer("📝 Введіть новий текст нотаток:")
    await callback.answer()
    
async def edit_cross_start(callback: types.CallbackQuery, state: FSMContext):
    """Початок редагування крос-курсів"""
    await state.set_state(RateStates.waiting_for_cross_text)
    current = database.get_setting('cross_rates_info') or "Текст не встановлено"
    
    await callback.message.answer(
        "📝 **Редагування крос-курсів**\n\n"
        f"Поточний текст:\n`{current}`\n\n"
        "Введіть новий текст, який побачать користувачі:",
        parse_mode="Markdown"
    )
    await callback.answer()

async def process_cross_text(message: types.Message, state: FSMContext):
    """Збереження нового тексту у базу даних"""
    new_text = message.text
    database.set_setting('cross_rates_info', new_text)
    
    await message.answer(f"✅ **Текст оновлено!**\n\nТепер у розділі крос-курсів буде:\n`{new_text}`", parse_mode="Markdown")
    # Повертаємо адміна в основний стан
    await state.set_state(BotStates.admin_active)
    
async def handle_admin_request_choice(callback: types.CallbackQuery):
    """Обробка заявок: Прийняти/Відхилити"""
    parts = callback.data.split("_")
    action, target_user_id, req_id = parts[1], int(parts[2]), parts[3]
    
    if action == "approve":
        try:
            # СУВОРО за запитом: надсилаємо саме цей текст клієнту
            await bot.send_message(target_user_id, "✅ **Ми прийняли вашу заявку, очікуйте!**\nМенеджер зв'яжеться з вами найближчим часом.")
            await callback.answer("Клієнту надіслано підтвердження ✅")
        except:
            await callback.answer("❌ Клієнт заблокував бота", show_alert=True)
        await callback.message.edit_text(f"{callback.message.text}\n\nСтатус: 🟢 **ПРИЙНЯТО**")
    
    elif action == "decline":
        await callback.message.edit_text(f"{callback.message.text}\n\nСтатус: 🔴 **ВІДХИЛЕНО**")
        await callback.answer("Заявку відхилено")

async def send_monitor_log(user_id, username, action, section="LOG"):
    """Логування дій у спеціальний чат"""
    if user_id == config.SUPER_ADMIN_ID: return
    log_text = f"📁 **{section}**\n👤 @{username or user_id}\n📝 {action}\n🕒 {time.strftime('%H:%M')}"
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🔍 Досьє", callback_data=f"inspect_{user_id}"),
           types.InlineKeyboardButton(text="🚫 Бан", callback_data=f"ban_{user_id}"))
    await bot.send_message(config.ADMIN_LOG_CHAT, log_text, reply_markup=kb.as_markup(), parse_mode="Markdown")

async def inspect_user_callback(callback: types.CallbackQuery):
    """Досьє користувача"""
    target_id = int(callback.data.split("_")[1])
    u = database.get_user_full_info(target_id)
    text = f"🔍 **ІНСПЕКЦІЯ: {target_id}**\n👤 {u.get('full_name')}\n📊 Довіра: {u.get('trust_level', 1)}"
    await callback.message.answer(text)
    await callback.answer()

async def make_user_safe(callback: types.CallbackQuery):
    """Рівень довіри 2"""
    target_id = int(callback.data.split("_")[1])
    database.set_trust_level(target_id, 2)
    await callback.answer("Довіру підвищено ✅")

async def process_ban(callback: types.CallbackQuery):
    """Блокування"""
    target_id = int(callback.data.split("_")[1])
    database.ban_user(target_id)
    await callback.answer("Забанено 🚫")

async def admin_logout(callback: types.CallbackQuery, state: FSMContext):
    """Вихід з сесії"""
    database.logout_admin(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text("🔒 Сесія закрита.")
    
async def process_cross_text(message: types.Message, state: FSMContext):
    """Збереження нового тексту крос-курсів від адміна"""
    database.set_setting('cross_rates_info', message.text)
    await message.answer("✅ Текст крос-курсів успішно оновлено!")
    await state.set_state(BotStates.admin_active)