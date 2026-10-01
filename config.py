import os
from dotenv import load_dotenv

load_dotenv()

# Дані для розділу "Контакти" та "Тех.підтримка"
CONTACT_PHONE = "+380688854679"      # Твій контактний номер
MANAGER_USERNAME = "Anred56"  # Юзернейм менеджера без @
SUPPORT_USERNAME = "Anred56"  # Юзернейм техпідтримки без @

# --- ОСНОВНІ ТОКЕНИ ---
API_TOKEN = os.getenv("API_TOKEN")

# --- БЕЗПЕКА ТА ДОСТУП ---
# Пароль для входу в адмін-панель через /login
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# ID Головного адміна (Owner), який невидимий для інших і має повний доступ
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", 0))

# ID чату або особистий ID куди будуть приходити всі логи моніторингу (Live-екран)
ADMIN_LOG_CHAT = int(os.getenv("ADMIN_LOG_CHAT", SUPER_ADMIN_ID))

# Основний ID для отримання заявок на обмін (якщо відрізняється від логів)
ADMIN_ID = int(os.getenv("ADMIN_ID", SUPER_ADMIN_ID))

# --- ЛІМІТИ ТА НАЛАШТУВАННЯ ---
MAX_ADMINS = 4  # Максимальна кількість додаткових адмінів
FLOOD_LIMIT = 5  # Кількість повідомлень в секунду до авто-бану

# Список ID адмінів, яким дозволено використовувати /login (білий список)
# Можна додати кілька ID через кому в .env: ADMIN_IDS=123,456,789
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in admin_ids_raw.split(",") if i.strip()]

# Не забуваємо додати самого себе в список дозволених, якщо ми не Owner
if SUPER_ADMIN_ID not in ADMIN_IDS:
    ADMIN_IDS.append(SUPER_ADMIN_ID)