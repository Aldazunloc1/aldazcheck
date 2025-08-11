import os

# Configuración del Bot
BOT_TOKEN = os.getenv('BOT_TOKEN', 'tu_token_aqui')
API_KEY = os.getenv('API_KEY', 'tu_api_key_aqui')
API_ENDPOINT = "https://alpha.imeicheck.com/api/php-api/create"

# Configuración de Logs
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/bot.log'

# Configuración de Rate Limiting
MAX_REQUESTS_PER_USER = 5
RATE_LIMIT_WINDOW = 3600  # 1 hora

# Administradores del Bot
ADMIN_IDS = [123456789, 987654321]  # IDs de Telegram de los admins

# Mensajes Personalizados
WELCOME_MESSAGE = """
🤖 **¡Bienvenido al Device Checker Bot!**
Tu bot personalizado para verificación de dispositivos.
"""

# Base de datos (opcional)
DATABASE_URL = os.getenv('DATABASE_URL', None)