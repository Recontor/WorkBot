from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database
import config
from bot import bot
from handlers import BotStates, main_menu, get_cancel_kb

async def operation_type_handler(event, state: FSMContext):
    """Головна таблиця курсів"""
    is_callback = isinstance(event, types.CallbackQuery)
    message = event.message if is_callback else event
    
    currencies = [
        ("USD_NEW", "🇺🇸 USD Новий"), ("USD_OLD", "🇺🇸 USD Білий"),
        ("EUR", "🇪🇺 EURO"), ("PLN", "🇵🇱 PLN"), ("GBP", "🇬🇧 GBP"),
        ("CHF", "🇨🇭 CHF"), ("CAD", "🇨🇦 CAD"), ("CZK", "🇨🇿 CZK"), ("SEK", "🇸🇪 SEK")
    ]
    
    table_text = "<b>📊 АКТУАЛЬНИЙ КУРС ВАЛЮТ</b>\n"
    table_text += "<code>Валюта       | Купівля | Продаж </code>\n"
    table_text += "<code>--------------------------------</code>\n"
    
    found_any = False
    for code, name in currencies:
        r = database.get_rate(code)
        if r:
            table_text += f"<code>{name:<12} | {r['buy']:>7.2f} | {r['sell']:>7.2f}</code>\n"
            found_any = True
        else:
            table_text += f"<code>{name:<12} |  -----  |  -----  </code>\n"
    
    table_text += "<code>--------------------------------</code>\n"
    if found_any:
        table_text += "<b>🔥 ОПТ (від 1000$): курси вигідніші!</b>\n"
    
    cross_info = database.get_setting('cross_rates_info') or "Уточнюйте"
    table_text += f"\n🔄 <b>Крос-курси:</b>\n<code>{cross_info}</code>"

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔵 КУПИТИ", callback_data="calc_buy"),
                types.InlineKeyboardButton(text="🔴 ПРОДАТИ", callback_data="calc_sell"))
    builder.row(types.InlineKeyboardButton(text="🧮 Розрахувати", callback_data="calc_start"),
                types.InlineKeyboardButton(text="📝 Лишити заявку", callback_data="start_free_request"))
    builder.row(types.InlineKeyboardButton(text="🔄 Крос-курси", callback_data="mode_cross"),
                types.InlineKeyboardButton(text="⬅️ Назад", callback_data="to_main"))

    if is_callback:
        await message.edit_text(table_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(table_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        
async def select_currency_for_calc(callback: types.CallbackQuery, state: FSMContext):
    """Вибір валюти для розрахунку після натискання Купити/Продати/Розрахувати"""
    mode = "buy" if "buy" in callback.data else "sell"
    await state.update_data(calc_mode=mode)
    
    builder = InlineKeyboardBuilder()
    currencies = [("USD_NEW", "USD Новий"), ("USD_OLD", "USD Білий"), ("EUR", "EUR"), ("PLN", "PLN"), ("GBP", "GBP")]
    for code, name in currencies:
        builder.add(types.InlineKeyboardButton(text=name, callback_data=f"curr_{code}"))
    
    builder.adjust(2)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="mode_uah"))
    await callback.message.edit_text(f"🧮 Ви обрали: **{'КУПІВЛЮ' if mode=='buy' else 'ПРОДАЖ'}**\nОберіть валюту:", reply_markup=builder.as_markup(), parse_mode="Markdown")

async def process_amount_entry(callback: types.CallbackQuery, state: FSMContext):
    """Запит суми для розрахунку"""
    currency_code = callback.data.replace("curr_", "")
    await state.update_data(selected_curr=currency_code)
    await state.set_state(BotStates.waiting_for_amount)
    
    # Використовуємо HTML замість Markdown, щоб уникнути помилок з символом "_"
    await callback.message.answer(
        f"💰 Введіть суму <b>{currency_code}</b>, яку хочете обміняти:", 
        reply_markup=get_cancel_kb(), 
        parse_mode="HTML"
    )
    await callback.answer()
    
async def calculate_result_handler(message: types.Message, state: FSMContext):
    """Сам розрахунок та вивід результату"""
    try:
        amount = float(message.text.replace(",", "."))
        data = await state.get_data()
        rate_data = database.get_rate(data['selected_curr'])
        
        # Визначаємо, чи це опт (від 1000)
        is_opt = amount >= 1000
        rate = rate_data['buy_opt'] if data['calc_mode'] == 'buy' and is_opt else \
               rate_data['buy'] if data['calc_mode'] == 'buy' else \
               rate_data['sell_opt'] if is_opt else rate_data['sell']
        
        result = amount * rate
        text = (
            f"✅ **РЕЗУЛЬТАТ РОЗРАХУНКУ**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💵 Валюта: {data['selected_curr']}\n"
            f"📈 Курс: `{rate}` {'(ОПТ 🔥)' if is_opt else ''}\n"
            f"💰 Сума: `{amount}`\n"
            f"➡️ **До отриманння: {result:.2f} UAH**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Бажаєте оформити заявку за цим курсом?"
        )
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="📝 Оформити заявку", callback_data="start_free_request"))
        builder.row(types.InlineKeyboardButton(text="⬅️ В меню", callback_data="to_main"))
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        await state.clear()
    except:
        await message.answer("❌ Будь ласка, введіть число (наприклад: 500 або 1200.50)")
        
async def start_free_request_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_req_phone)
    await callback.message.answer("📱 **Крок 1/4: Номер телефону**\nВведіть ваш номер (тільки цифри):", reply_markup=get_cancel_kb())
    await callback.answer()

async def process_req_phone(message: types.Message, state: FSMContext):
    raw_phone = message.text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not raw_phone.lstrip('+').isdigit():
        await message.answer("❌ Введіть номер цифрами (напр. 380...):")
        return
    await state.update_data(r_phone=raw_phone)
    await state.set_state(BotStates.waiting_for_req_currency)
    await message.answer("💱 **Крок 2/4: Валюта**\nЯку валюту міняємо?")

async def process_req_currency(message: types.Message, state: FSMContext):
    await state.update_data(r_curr=message.text)
    await state.set_state(BotStates.waiting_for_req_amount)
    await message.answer("💰 **Крок 3/4: Сума**\nЯку суму плануєте?")

async def process_req_amount(message: types.Message, state: FSMContext):
    await state.update_data(r_amount=message.text)
    await state.set_state(BotStates.waiting_for_req_text)
    await message.answer("✍️ **Крок 4/4: Коментар**\nВаш текст (або 'немає'):")

async def process_req_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    u_mention = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
    details = f"Валюта: {data['r_curr']} | Сума: {data['r_amount']} | Текст: {message.text}"
    req_id = database.save_exchange_request(user.id, user.username or "id"+str(user.id), data['r_phone'], details)
    
    admin_text = (f"🔔 **НОВА ЗАЯВКА №{req_id}**\n━━━━━━━━━━━━━━━━━━\n"
                  f"👤 Клієнт: {u_mention}\n📞 Тел: `{data['r_phone']}`\n💵 Деталі: {details}")
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Прийняти", callback_data=f"req_approve_{user.id}_{req_id}"),
                types.InlineKeyboardButton(text="❌ Відхилити", callback_data=f"req_decline_{user.id}_{req_id}"))

    await bot.send_message(config.ADMIN_ID, admin_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await message.answer("✅ **Ми прийняли вашу заявку, очікуйте!**\nМенеджер зв'яжеться з вами.", reply_markup=main_menu)
    await state.clear()
    
async def cross_mode_handler(callback: types.CallbackQuery):
    """Відображення вікна з крос-курсами"""
    cross_info = database.get_setting('cross_rates_info') or "Інформація оновлюється..."
    
    text = (
        "🔄 **АКТУАЛЬНІ КРОС-КУРСИ**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"<code>{cross_info}</code>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👉 *Курси вказані для ознайомлення.*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад до курсів", callback_data="mode_uah"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()