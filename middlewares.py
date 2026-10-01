import time
import logging
from aiogram import BaseMiddleware, types
from collections import defaultdict
import database
import config

user_request_times = defaultdict(list)

class AntiFloodMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if not user:
            return await handler(event, data)

        user_id = user.id
        now = time.time()

        if database.is_user_banned(user_id):
            return 

        user_request_times[user_id] = [t for t in user_request_times[user_id] if now - t < 1.0]
        user_request_times[user_id].append(now)

        if len(user_request_times[user_id]) > config.FLOOD_LIMIT:
            if len(user_request_times[user_id]) > (config.FLOOD_LIMIT * 2):
                database.ban_user(user_id)
                return
            return 

        return await handler(event, data)

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if not user:
            return await handler(event, data)

        if isinstance(event, types.Message):
            action_text = event.text or "Медіа"
            if event.text:
                database.log_message(user.id, event.text)
        elif isinstance(event, types.CallbackQuery):
            action_text = f"Кнопка: {event.data}"
        else:
            action_text = "Взаємодія"

        logging.info(f"User {user.id}: {action_text[:50]}")

        database.register_user_activity(
            user.id, 
            user.username, 
            user.full_name, 
            user.language_code, 
            getattr(user, 'is_premium', False)
        )

        return await handler(event, data)