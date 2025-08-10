from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    ContextTypes, filters, ConversationHandler
)
import requests

load_dotenv()

# Configuración
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
# Lee la variable de entorno como string, luego convierte a lista de enteros
authorized_users_str = os.getenv("AUTHORIZED_USER_IDS", "")
AUTHORIZED_USER_IDS = [int(uid) for uid in authorized_users_str.split(",") if uid.strip().isdigit()]

MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos

# Estados para ConversationHandler
SELECTING_SERVICE, ENTERING_IMEI, CONFIRMING_ORDER = range(3)

SERVICIOS = {
    "1": {"name": "Find My iPhone [ FMI ] (ON/OFF)", "category": "Apple"},
    "2": {"name": "Warranty + Activation - PRO [IMEI/SN]", "category": "Apple"},
    "3": {"name": "Apple FULL INFO [No Carrier]", "category": "Apple"},
    "4": {"name": "iCloud Clean/Lost Check", "category": "Apple"},
    "5": {"name": "Blacklist Status (GSMA)", "category": "General"},
    "6": {"name": "Blacklist Pro Check (GSMA)", "category": "General"},
    "7": {"name": "Apple Carrier + SimLock - back-up", "category": "Apple"},
    "8": {"name": "Samsung Info (S1) (IMEI)", "category": "Samsung"},
    "9": {"name": "SOLD BY + GSX Apple", "category": "Apple"},
    "10": {"name": "IMEI to Model [all brands][IMEI/SN]", "category": "General"},
    "11": {"name": "IMEI to Brand/Model/Name", "category": "General"},
    "12": {"name": "GSX Next Tether + iOS (GSX Carrier)", "category": "Apple"},
    "13": {"name": "Model + Color + Storage + FMI", "category": "Apple"},
    "14": {"name": "IMEI to SN (Full Convertor)", "category": "General"},
    "15": {"name": "T-mobile (ESN) PRO Check", "category": "Carrier"},
    "16": {"name": "Verizon (ESN) Clean/Lost Status", "category": "Carrier"},
    "17": {"name": "Huawei IMEI Info", "category": "Huawei"},
    "18": {"name": "iMac FMI Status On/Off", "category": "Apple"},
    "19": {"name": "Apple FULL INFO [+Carrier] B", "category": "Apple"},
    "20": {"name": "Apple SimLock Check", "category": "Apple"},
    "21": {"name": "SAMSUNG INFO & KNOX STATUS (S2)", "category": "Samsung"},
    "22": {"name": "Apple BASIC INFO (PRO) - new", "category": "Apple"},
    "23": {"name": "Apple Carrier Check (S2)", "category": "Apple"},
    "25": {"name": "XIAOMI MI LOCK & INFO", "category": "Xiaomi"},
    "27": {"name": "ONEPLUS IMEI INFO", "category": "OnePlus"},
    "33": {"name": "Replacement Status (Active Device)", "category": "Apple"},
    "34": {"name": "Replaced Status (Original Device)", "category": "Apple"},
    "36": {"name": "Samsung Info (S1) + Blacklist", "category": "Samsung"},
    "37": {"name": "Samsung Info & KNOX STATUS (S1)", "category": "Samsung"},
    "39": {"name": "APPLE FULL INFO [+Carrier] A", "category": "Apple"},
    "41": {"name": "MDM Status ON/OFF", "category": "Apple"},
    "46": {"name": "MDM Status ON/OFF + GSX Policy + FMI", "category": "Apple"},
    "47": {"name": "Apple FULL + MDM + GSMA PRO", "category": "Apple"},
    "50": {"name": "Apple SERIAL Info(model,size,color)", "category": "Apple"},
    "51": {"name": "Warranty + Activation [SN ONLY]", "category": "Apple"},
    "52": {"name": "Model Description (Any Apple SN/IMEI)", "category": "Apple"},
    "55": {"name": "Blacklist Status - cheap", "category": "General"},
    "57": {"name": "Google Pixel Info", "category": "Google"},
    "58": {"name": "Honor Info", "category": "Honor"},
    "59": {"name": "Realme Info", "category": "Realme"},
    "60": {"name": "Oppo Info", "category": "Oppo"},
    "61": {"name": "Apple Demo Unit Device Info", "category": "Apple"},
    "62": {"name": "EID INFO (IMEI TO EID)", "category": "General"},
    "63": {"name": "Motorola Info", "category": "Motorola"}
}

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SERVICES_PER_PAGE = 8

class IMEIValidator:
    @staticmethod
    def is_valid_imei(imei: str) -> bool:
        """Valida formato IMEI básico"""
        imei = re.sub(r'\D', '', imei)
        return len(imei) >= 10 and len(imei) <= 20

    @staticmethod
    def clean_imei(imei: str) -> str:
        """Limpia y normaliza el IMEI"""
        return re.sub(r'\D', '', imei.strip())

class APIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'IMEI-Bot/1.0'})

    async def create_instant_order(self, service_id: str, imei: str) -> Optional[Dict]:
        """📤 Instant Order API Endpoint - Crea una orden instantánea"""
        url = f"https://alpha.imeicheck.com/api/php-api/create"
        params = {
            'key': self.api_key,
            'service': service_id,
            'imei': imei
        }
        
        logger.info(f"Creando orden instantánea - Servicio: {service_id}, IMEI: {imei}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Respuesta API Create: {result}")
                
                # Verificar respuesta según documentación
                if isinstance(result, dict):
                    if result.get('status') == 'success' or 'order_id' in result:
                        return result
                    elif result.get('status') == 'failed':
                        logger.error(f"Orden falló: {result}")
                        return {'error': 'order_failed', 'message': 'La orden fue rechazada'}
                    elif result.get('status') == 'error':
                        error_msg = result.get('message', 'Error del sistema')
                        logger.error(f"Error del sistema: {error_msg}")
                        return {'error': 'system_error', 'message': error_msg}
                
                return result
                
            except Exception as e:
                logger.warning(f"Intento {attempt + 1} falló: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    return {'error': 'connection_error', 'message': str(e)}
        
        return None

    async def get_order_history(self, order_id: str) -> Optional[Dict]:
        """📜 Order History API Endpoint - Consulta historial de orden"""
        url = f"https://alpha.imeicheck.com/api/php-api/history"
        params = {
            'key': self.api_key,
            'orderId': order_id
        }
        
        logger.info(f"Consultando historial de orden: {order_id}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Respuesta API History: {result}")
                return result
                
            except Exception as e:
                logger.warning(f"Intento {attempt + 1} falló: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
        
        return None

# Inicializar cliente API
api_client = APIClient(API_KEY)

def get_categories_keyboard():
    """Teclado de categorías"""
    categories = set(service["category"] for service in SERVICIOS.values())
    keyboard = []
    
    for category in sorted(categories):
        keyboard.append([InlineKeyboardButton(f"📱 {category}", callback_data=f"cat_{category}")])
    
    keyboard.append([InlineKeyboardButton("📋 Ver Todos", callback_data="cat_all")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)

def get_services_keyboard(page: int = 0, category: str = None):
    """Teclado de servicios con paginación y filtrado por categoría"""
    if category and category != "all":
        filtered_services = {k: v for k, v in SERVICIOS.items() if v["category"] == category}
    else:
        filtered_services = SERVICIOS

    service_items = list(filtered_services.items())
    start = page * SERVICES_PER_PAGE
    end = start + SERVICES_PER_PAGE
    keyboard = []

    for service_id, service_info in service_items[start:end]:
        button_text = f"{service_id} - {service_info['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"service_{service_id}")])

    # Navegación
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"page_{page - 1}_{category or 'all'}"))
    if end < len(service_items):
        nav_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"page_{page + 1}_{category or 'all'}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)

    # Botones de control
    control_buttons = []
    if category and category != "all":
        control_buttons.append(InlineKeyboardButton("🔙 Categorías", callback_data="back_categories"))
    control_buttons.append(InlineKeyboardButton("❌ Cancelar", callback_data="cancel"))
    
    keyboard.append(control_buttons)

    return InlineKeyboardMarkup(keyboard)

def is_authorized(user_id: int) -> bool:
    """Verifica si el usuario está autorizado"""
    return user_id in AUTHORIZED_USER_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return ConversationHandler.END

    welcome_msg = (
        "🤖 <b>Bienvenido al Bot IMEI Check</b>\n\n"
        "🔍 Comandos disponibles:\n"
        "• /services - Ver servicios disponibles\n"
        "• /help - Ayuda y información\n"
        "• /cancel - Cancelar operación actual\n\n"
        "✨ <i>¡Listo para hacer consultas IMEI!</i>"
    )
    
    await update.message.reply_html(welcome_msg)
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de ayuda"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return

    help_text = (
        "📖 <b>Ayuda - Bot IMEI Check</b>\n\n"
        "<b>🔧 Cómo usar:</b>\n"
        "1️⃣ Usa /services para ver servicios\n"
        "2️⃣ Selecciona una categoría o servicio\n"
        "3️⃣ Introduce el IMEI cuando se solicite\n"
        "4️⃣ Confirma y obtén el resultado instantáneo\n\n"
        "<b>📱 Formatos IMEI válidos:</b>\n"
        "• 15 dígitos: 123456789012345\n"
        "• Con guiones: 12-345678-901234-5\n"
        "• Serial Apple también soportado\n\n"
        "<b>💡 Consejos:</b>\n"
        "• Los resultados son instantáneos\n"
        "• Usa /cancel para cancelar en cualquier momento"
    )
    
    await update.message.reply_html(help_text)

async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para mostrar servicios"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📋 <b>Selecciona una categoría:</b>",
        reply_markup=get_categories_keyboard(),
        parse_mode="HTML"
    )
    return SELECTING_SERVICE

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la selección de categoría"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_authorized(user_id):
        await query.edit_message_text("🚫 No tienes permiso para usar este bot.")
        return ConversationHandler.END

    category = query.data.replace("cat_", "")
    context.user_data["selected_category"] = category
    
    if category == "all":
        title = "📋 <b>Todos los Servicios:</b>"
    else:
        title = f"📱 <b>Servicios - {category}:</b>"

    await query.edit_message_text(
        title,
        reply_markup=get_services_keyboard(0, category),
        parse_mode="HTML"
    )
    return SELECTING_SERVICE

async def pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la paginación"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_authorized(user_id):
        await query.edit_message_text("🚫 No tienes permiso para usar este bot.")
        return ConversationHandler.END

    data_parts = query.data.split("_")
    page = int(data_parts[1])
    category = data_parts[2] if len(data_parts) > 2 else "all"

    await query.edit_message_reply_markup(
        reply_markup=get_services_keyboard(page, category)
    )
    return SELECTING_SERVICE

async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la selección de servicio"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_authorized(user_id):
        await query.edit_message_text("🚫 No tienes permiso para usar este bot.")
        return ConversationHandler.END

    service_id = query.data.replace("service_", "")
    service_info = SERVICIOS[service_id]
    context.user_data["selected_service"] = service_id

    confirmation_text = (
        f"✅ <b>Servicio seleccionado:</b>\n\n"
        f"🔧 <b>Nombre:</b> {service_info['name']}\n"
        f"📱 <b>Categoría:</b> {service_info['category']}\n\n"
        f"📝 <b>Ahora envía el IMEI o Serial Number</b>\n\n"
        f"<i>Formato: solo números (ej: 123456789012345)</i>"
    )

    await query.edit_message_text(confirmation_text, parse_mode="HTML")
    return ENTERING_IMEI

async def imei_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el IMEI recibido"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return ConversationHandler.END

    if "selected_service" not in context.user_data:
        await update.message.reply_text(
            "⚠️ Primero selecciona un servicio con /services"
        )
        return ConversationHandler.END

    imei_raw = update.message.text.strip()
    imei = IMEIValidator.clean_imei(imei_raw)
    
    # Validación básica
    if not IMEIValidator.is_valid_imei(imei):
        await update.message.reply_text(
            "❌ <b>IMEI/Serial inválido</b>\n\n"
            "Por favor, introduce un IMEI válido (10-20 dígitos) o un Serial Number.",
            parse_mode="HTML"
        )
        return ENTERING_IMEI

    service_id = context.user_data["selected_service"]
    service_info = SERVICIOS[service_id]
    
    # Confirmación antes de procesar
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm_{imei}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel")
        ]
    ])

    confirm_text = (
        f"🔍 <b>Confirmar Consulta</b>\n\n"
        f"📱 <b>IMEI/SN:</b> <code>{imei}</code>\n"
        f"🔧 <b>Servicio:</b> {service_info['name']}\n\n"
        f"¿Proceder con la consulta instantánea?"
    )

    await update.message.reply_html(confirm_text, reply_markup=keyboard)
    return CONFIRMING_ORDER

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma y procesa la orden instantánea"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_authorized(user_id):
        await query.edit_message_text("🚫 No tienes permiso para usar este bot.")
        return ConversationHandler.END

    imei = query.data.replace("confirm_", "")
    service_id = context.user_data["selected_service"]
    service_info = SERVICIOS[service_id]

    # Mensaje de procesamiento
    processing_msg = (
        f"📤 <b>Procesando orden instantánea...</b>\n\n"
        f"📱 IMEI: <code>{imei}</code>\n"
        f"🔧 Servicio: {service_info['name']}\n\n"
        f"⏳ <i>Creando orden...</i>"
    )
    
    await query.edit_message_text(processing_msg, parse_mode="HTML")

    # 📤 Crear orden instantánea
    create_result = await api_client.create_instant_order(service_id, imei)
    
    if not create_result:
        error_msg = (
            f"❌ <b>Error de conexión</b>\n\n"
            f"No se pudo conectar con el servidor. "
            f"Por favor intenta nuevamente."
        )
        await query.edit_message_text(error_msg, parse_mode="HTML")
        return ConversationHandler.END

    # Verificar errores del sistema
    if 'error' in create_result:
        error_type = create_result.get('error')
        error_message = create_result.get('message', 'Error desconocido')
        
        if error_type == 'system_error':
            error_msg = (
                f"❌ <b>Error del Sistema</b>\n\n"
                f"Se produjo un error:\n"
                f"• API Key inválida\n"
                f"• Dirección IP incorrecta\n"
                f"• Créditos insuficientes\n\n"
                f"Por favor contacta al administrador."
            )
        elif error_type == 'order_failed':
            error_msg = (
                f"❌ <b>Orden Rechazada</b>\n\n"
                f"La orden fue rechazada por el sistema.\n"
                f"Verifica el IMEI e intenta nuevamente."
            )
        else:
            error_msg = (
                f"❌ <b>Error</b>\n\n"
                f"No se pudo procesar la consulta.\n"
                f"Intenta nuevamente más tarde."
            )
        
        await query.edit_message_text(error_msg, parse_mode="HTML")
        return ConversationHandler.END

    # Obtener order_id
    order_id = create_result.get('order_id')
    if not order_id:
        error_msg = (
            f"❌ <b>Error en respuesta</b>\n\n"
            f"No se recibió ID de orden válido."
        )
        await query.edit_message_text(error_msg, parse_mode="HTML")
        return ConversationHandler.END

    logger.info(f"Orden instantánea creada exitosamente: {order_id}")

    # Actualizar mensaje
    await query.edit_message_text(
        f"📜 <b>Consultando historial...</b>\n\n"
        f"📱 IMEI: <code>{imei}</code>\n"
        f"🆔 Order ID: <code>{order_id}</code>\n\n"
        f"⏳ <i>Obteniendo resultado...</i>",
        parse_mode="HTML"
    )

    # 📜 Consultar historial de la orden
    history_result = await api_client.get_order_history(order_id)
    
    if not history_result:
        error_msg = (
            f"❌ <b>Error consultando resultado</b>\n\n"
            f"📱 IMEI: <code>{imei}</code>\n"
            f"🆔 Order ID: <code>{order_id}</code>\n\n"
            f"No se pudo obtener el resultado. Intenta más tarde."
        )
        await query.edit_message_text(error_msg, parse_mode="HTML")
        return ConversationHandler.END

    # Enviar resultado
    await send_result(query, history_result, imei, order_id)
    return ConversationHandler.END

async def send_result(query, result_data: Dict, imei: str, order_id: str):
    """Envía el resultado de la consulta (sin mostrar créditos ni costos)"""
    try:
        # Extraer información básica (sin credit ni balance)
        service_name = result_data.get("service_name", "N/A")
        status = result_data.get("status", "N/A")
        created_at = result_data.get("created_at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        updated_at = result_data.get("updated_at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        result_html = result_data.get("result", "")

        # Verificar si hay resultado
        if not result_html or result_html.strip() == "":
            error_msg = (
                f"❌ <b>Sin resultados</b>\n\n"
                f"📱 IMEI: <code>{imei}</code>\n"
                f"🆔 Order ID: <code>{order_id}</code>\n\n"
                f"La consulta no devolvió resultados."
            )
            await query.edit_message_text(error_msg, parse_mode="HTML")
            return

        # Extraer URL de imagen del HTML
        img_url = None
        img_match = re.search(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>', result_html, re.IGNORECASE)
        if img_match:
            img_url = img_match.group(1)
            # Decodificar caracteres escapados en la URL
            img_url = img_url.replace('\\/', '/')

        # Procesar el HTML del resultado para mostrar texto limpio
        # Convertir <br> a saltos de línea
        formatted_result = result_html.replace('<br>', '\n').replace('<BR>', '\n')
        
        # Remover imagen del texto
        formatted_result = re.sub(r'<img[^>]*>', '', formatted_result, flags=re.IGNORECASE)
        
        # Convertir algunos estilos HTML a emojis de Telegram
        formatted_result = re.sub(r'<span[^>]*color\s*:\s*green[^>]*>(.*?)</span>', r'✅ \1', formatted_result, flags=re.IGNORECASE)
        formatted_result = re.sub(r'<span[^>]*color\s*:\s*red[^>]*>(.*?)</span>', r'❌ \1', formatted_result, flags=re.IGNORECASE)
        formatted_result = re.sub(r'<span[^>]*color\s*:\s*orange[^>]*>(.*?)</span>', r'⚠️ \1', formatted_result, flags=re.IGNORECASE)
        formatted_result = re.sub(r'<font[^>]*color\s*=\s*["\']red["\'][^>]*>(.*?)</font>', r'❌ \1', formatted_result, flags=re.IGNORECASE)
        
        # Remover todas las demás etiquetas HTML
        formatted_result = re.sub(r'<[^>]+>', '', formatted_result)
        
        # Limpiar espacios extra y líneas vacías
        formatted_result = '\n'.join([line.strip() for line in formatted_result.split('\n') if line.strip()])

        # Construir mensaje de respuesta (SIN CRÉDITOS NI COSTOS)
        header_text = (
            f"✅ <b>Consulta Completada</b>\n\n"
            f"📌 <b>Servicio:</b> {service_name}\n"
            f"📱 <b>IMEI:</b> <code>{imei}</code>\n"
            f"📊 <b>Estado:</b> {status}\n"
            f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
            f"🗓 <b>Creado:</b> {created_at}\n"
            f"🔄 <b>Actualizado:</b> {updated_at}\n"
            f"{'═' * 30}\n"
        )

        # Construir el resultado completo
        full_result = header_text + formatted_result

        # Verificar longitud del mensaje (Telegram límite: 4096 caracteres)
        if len(full_result) > 4000:
            # Si es muy largo, dividir el mensaje
            await query.edit_message_text(header_text, parse_mode="HTML")
            
            # Enviar resultado en chunks
            chunks = [formatted_result[i:i+3800] for i in range(0, len(formatted_result), 3800)]
            for chunk in chunks:
                await query.message.reply_text(f"<pre>{chunk}</pre>", parse_mode="HTML")
        else:
            # Enviar imagen si existe, sino solo texto
            if img_url and img_url.startswith(('http', 'https')):
                try:
                    await query.message.reply_photo(
                        photo=img_url,
                        caption=full_result,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"Error enviando imagen {img_url}: {e}")
                    await query.edit_message_text(full_result, parse_mode="HTML")
            else:
                await query.edit_message_text(full_result, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error enviando resultado: {e}")
        error_msg = (
            f"❌ <b>Error procesando resultado</b>\n\n"
            f"📱 IMEI: <code>{imei}</code>\n"
            f"🆔 Order ID: <code>{order_id}</code>\n\n"
            f"La consulta se completó pero hubo un error al mostrar los resultados.\n\n"
            f"<b>Error:</b> {str(e)}"
        )
        await query.edit_message_text(error_msg, parse_mode="HTML")

async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la operación actual"""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ <b>Operación cancelada</b>\n\n"
            "Usa /services para comenzar una nueva consulta.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_html(
            "❌ <b>Operación cancelada</b>\n\n"
            "Usa /services para comenzar una nueva consulta."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Regresa al menú de categorías"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📋 <b>Selecciona una categoría:</b>",
        reply_markup=get_categories_keyboard(),
        parse_mode="HTML"
    )
    return SELECTING_SERVICE

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja comandos no reconocidos"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return

    await update.message.reply_html(
        "❓ <b>Comando no reconocido</b>\n\n"
        "Usa /services para comenzar una consulta IMEI."
    )

async def set_bot_commands(application):
    """Configura los comandos del bot"""
    commands = [
        BotCommand("start", "Iniciar el bot"),
        BotCommand("services", "Ver servicios disponibles"),
        BotCommand("help", "Ayuda y información"),
        BotCommand("cancel", "Cancelar operación actual"),
    ]
    
    try:
        await application.bot.set_my_commands(commands)
        logger.info("✅ Comandos del bot configurados correctamente")
    except Exception as e:
        logger.error(f"❌ Error configurando comandos del bot: {e}")

def main():
    """Función principal"""
    # Validar configuración
    if not TOKEN:
        logger.error("❌ TOKEN del bot no configurado")
        return
    
    if not API_KEY:
        logger.error("❌ API_KEY no configurado")
        return
    
    if not AUTHORIZED_USER_IDS:
        logger.error("❌ AUTHORIZED_USER_IDS no configurado")
        return

    # Crear aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Agregar handler de errores
    async def error_handler(update, context):
        """Handler global de errores"""
        logger.error(f"Error en update {update}: {context.error}")
    
    application.add_error_handler(error_handler)

    # Configurar ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('services', services_command),
        ],
        states={
            SELECTING_SERVICE: [
                CallbackQueryHandler(category_selected, pattern=r"^cat_"),
                CallbackQueryHandler(pagination_handler, pattern=r"^page_"),
                CallbackQueryHandler(service_selected, pattern=r"^service_"),
                CallbackQueryHandler(back_to_categories, pattern="^back_categories$"),
                CallbackQueryHandler(cancel_operation, pattern="^cancel$"),
            ],
            ENTERING_IMEI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, imei_received),
                CallbackQueryHandler(cancel_operation, pattern="^cancel$"),
            ],
            CONFIRMING_ORDER: [
                CallbackQueryHandler(confirm_order, pattern=r"^confirm_"),
                CallbackQueryHandler(cancel_operation, pattern="^cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_operation),
            CallbackQueryHandler(cancel_operation, pattern="^cancel$"),
        ],
        per_message=False,
        per_chat=True,
        per_user=True,
    )

    # Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command))

    # Log de configuración
    logger.info("🤖 Bot IMEI Check iniciando...")
    logger.info(f"📊 Servicios disponibles: {len(SERVICIOS)}")
    logger.info(f"👥 Usuarios autorizados: {len(AUTHORIZED_USER_IDS)}")

    # Configurar función de inicialización
    async def post_init(application):
        await set_bot_commands(application)
        # Eliminar webhook si existe
        try:
            logger.info("🔄 Eliminando webhook existente...")
            await application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook eliminado correctamente")
        except Exception as e:
            logger.warning(f"⚠️ Error eliminando webhook: {e}")
    
    application.post_init = post_init

    # Ejecutar bot
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"❌ Error ejecutando el bot: {e}")

if __name__ == "__main__":
    main()