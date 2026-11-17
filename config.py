import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", 0))

# ID пользователей, которые являются преподавателями (админы)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# Для локального запуска используйте "sqlite:///diary.db"
# Для Netrun используйте "sqlite:////data/diary.db" (4 слэша)
DB_URL = "sqlite:////data/diary.db" 
