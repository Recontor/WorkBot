from aiogram import types
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import config

# Усі стани бота в одному місці
class BotStates(StatesGroup):
    admin_active = State()          # Активна сесія адміна
    waiting_for_amount = State()    # Очікування суми для калькулятора
    waiting_for_broadcast = State() # Текст розсилки
    
    # Стани для покрокової заявки
    waiting_for_req_phone = State()
    waiting_for_req_currency = State()
    waiting_for_req_amount = State()
    waiting_for_req_text = State()

def get_main_kb():
    """Головне меню 2х2"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text="💱 Курс валют"),
        types.KeyboardButton(text="📞 Контакти")
    )
    builder.row(
        types.KeyboardButton(text="ℹ️ Допомога"),
        types.KeyboardButton(text="👨‍💻 Тех.підтримка")
    )
    return builder.as_markup(resize_keyboard=True)

def get_cancel_kb():
    """Кнопка відміни для станів FSM"""
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Відмінити та в меню"))
    return builder.as_markup(resize_keyboard=True)

# Глобальна змінна для зручного доступу
main_menu = get_main_kb()

async def start_handler(message: types.Message):
    """Привітання при /start"""
    welcome_text = (
        f"👋 **Вітаємо, {message.from_user.first_name}!**\n\n"
        "Я — ваш надійний помічник у світі валют.\n"
        "📊 Актуальні курси, швидкий розрахунок та онлайн-заявки.\n\n"
        "Оберіть потрібний розділ меню нижче: 👇"
    )
    await message.answer(welcome_text, reply_markup=main_menu, parse_mode="Markdown")

async def contacts_handler(message: types.Message):
    """Розширений блок контактів з адресами та графіком"""
    text = (
        "📞 **НАШІ КОНТАКТИ ТА АДРЕСИ**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📱 **Телефон:** `{config.CONTACT_PHONE}`\n"
        f"✈️ **Telegram:** @{config.MANAGER_USERNAME}\n\n"
        
        "📍 **ВІДДІЛЕННЯ:**\n"
        "🏢 **Магазин шкіряних товарів та аксесуарів:** вул. Галицька 21, біля каштану\n"
        "⏰ Пн-Сб: 09:00 - 17:20\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔔 *Курс фіксується на 1 годину після підтвердження заявки менеджерoм.*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🗺 Відкрити мапу", url="https://www.google.com/maps/place/%D0%A2%D0%95%D0%A5%D0%9D%D0%9E%D0%9C%D0%90%D0%9A%D0%A1/@48.9029576,24.847234,20.99z/data=!4m6!3m5!1s0x4730c3810a21521f:0xe79873da4f87d0d9!8m2!3d48.9029898!4d24.8473387!16s%2Fg%2F11rcht2jcx?authuser=0&entry=ttu&g_ep=EgoyMDI2MDkwOS4wIKXMDSoASAFQAw%3D%3D"))
    builder.row(types.InlineKeyboardButton(text="✍️ Написати менеджеру", url=f"https://t.me/{config.MANAGER_USERNAME}"))
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

async def tech_support_handler(message: types.Message):
    """Обробник техпідтримки"""
    text = (
        "👨‍💻 **ТЕХНІЧНА ПІДТРИМКА**\n\n"
        "Виникли проблеми з ботом?\n"
        "Наш спеціаліст допоможе вам:\n\n"
        f"➡️ @{config.SUPPORT_USERNAME}"
    )
    await message.answer(text, parse_mode="Markdown")

async def help_handler(message: types.Message):
    """Розділ допомоги"""
    text = (
        "ℹ️ **ЯК ПРАЦЮЄ БОТ?**\n\n"
        "1️⃣ **Курс валют:** перегляд актуальних цін та ОПТу.\n"
        "2️⃣ **Розрахунок:** вкажіть суму, і бот порахує результат за поточним курсом.\n"
        "3️⃣ **Заявка:** заповніть коротку анкету, і менеджер зв'яжеться з вами для фіксації курсу.\n\n"
        "💡 *Всі операції конфіденційні та безпечні.*"
    )
    await message.answer(text, reply_markup=main_menu, parse_mode="Markdown")

async def cmd_cancel(message: types.Message, state: FSMContext = None):
    """Повернення в головне меню та скидання станів"""
    if state:
        await state.clear()
    await message.answer("🏠 Ви повернулися в головне меню.", reply_markup=main_menu)