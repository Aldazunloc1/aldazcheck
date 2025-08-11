import telebot
import requests
import json
import os
from telebot import types
import time
import logging
import re
import html
from datetime import datetime, timezone

# Configuración
BOT_TOKEN = "8189469555:AAHSTOC2MAnFV-SuXiZgADRgU2YUbbkmNh0"  # Reemplaza con tu token de bot
API_KEY = "Z2zMr-ZLlCh-NpNQj-7XoJh-ywo6g-cFUdo"      # Reemplaza con tu API key
API_ENDPOINT = "https://alpha.imeicheck.com/api/php-api/create"

# IDs de usuarios autorizados (administradores y usuarios premium)
AUTHORIZED_USERS = {
    7655366089: {"role": "admin", "name": "Admin Principal", "credits": -1},  # -1 = ilimitado
    6269867784: {"role": "premium", "name": "Usuario Premium", "credits": 100},
    # Agrega más usuarios autorizados aquí
}

# Archivos de datos JSON
DATA_FILES = {
    "users": "users_data.json",
    "queries": "queries_log.json", 
    "stats": "bot_stats.json",
    "auth": "authorized_users.json"
}

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# Servicios organizados por categorías con emojis y descripciones
SERVICES = {
    "apple": {
        "name": "🍎 Apple",
        "emoji": "🍎",
        "description": "Servicios para dispositivos Apple (iPhone, iPad, Mac)",
        "services": {
            "1": {"name": "Find My iPhone Status", "desc": "Verificar si FMI está activo/inactivo", "popular": True, "credits": 1},
            "2": {"name": "Warranty + Activation Info", "desc": "Estado de garantía y activación", "popular": True, "credits": 1},
            "3": {"name": "Apple FULL INFO", "desc": "Información completa sin carrier", "popular": True, "credits": 2},
            "4": {"name": "iCloud Clean/Lost Check", "desc": "Estado de iCloud y reporte", "popular": True, "credits": 1},
            "9": {"name": "SOLD BY + GSX Apple", "desc": "Información de venta y GSX", "credits": 3},
            "12": {"name": "GSX Next Tether + iOS", "desc": "Estado de tether y versión iOS", "credits": 2},
            "13": {"name": "Model + Color + Storage + FMI", "desc": "Especificaciones del dispositivo", "credits": 1},
            "18": {"name": "iMac FMI Status", "desc": "Find My para iMac", "credits": 1},
            "19": {"name": "Apple FULL INFO [+Carrier] B", "desc": "Info completa con carrier (versión B)", "credits": 3},
            "20": {"name": "Apple SimLock Check", "desc": "Estado de bloqueo SIM", "credits": 1},
            "22": {"name": "Apple BASIC INFO (PRO)", "desc": "Información básica profesional", "credits": 1},
            "23": {"name": "Apple Carrier Check", "desc": "Verificación de operadora", "credits": 1},
            "33": {"name": "Replacement Status (Active)", "desc": "Estado de reemplazo activo", "credits": 1},
            "34": {"name": "Replaced Status (Original)", "desc": "Estado de dispositivo reemplazado", "credits": 1},
            "39": {"name": "APPLE FULL INFO [+Carrier] A", "desc": "Info completa con carrier (versión A)", "credits": 3},
            "41": {"name": "MDM Status", "desc": "Estado de gestión móvil", "credits": 1},
            "46": {"name": "MDM + GSX Policy + FMI", "desc": "MDM completo con políticas", "credits": 2},
            "47": {"name": "Apple FULL + MDM + GSMA", "desc": "Información completa premium", "credits": 4},
            "50": {"name": "Apple SERIAL Info", "desc": "Info por número de serie", "credits": 1},
            "51": {"name": "Warranty [SN ONLY]", "desc": "Garantía solo con serial", "credits": 1},
            "52": {"name": "Model Description", "desc": "Descripción del modelo", "credits": 1},
            "61": {"name": "Apple Demo Unit Info", "desc": "Verificar unidad de demostración", "credits": 1}
        }
    },
    "samsung": {
        "name": "📱 Samsung",
        "emoji": "📱",
        "description": "Servicios para dispositivos Samsung Galaxy",
        "services": {
            "8": {"name": "Samsung Info (S1)", "desc": "Información básica Samsung", "popular": True, "credits": 1},
            "21": {"name": "Samsung INFO & KNOX STATUS", "desc": "Info completa + estado Knox", "popular": True, "credits": 2},
            "36": {"name": "Samsung Info + Blacklist", "desc": "Información con lista negra", "credits": 1},
            "37": {"name": "Samsung INFO & KNOX (S1)", "desc": "Info y Knox versión S1", "credits": 2}
        }
    },
    "general": {
        "name": "🌐 General",
        "emoji": "🌐",
        "description": "Servicios universales para cualquier marca",
        "services": {
            "5": {"name": "Blacklist Status (GSMA)", "desc": "Estado en lista negra GSMA", "popular": True, "credits": 1},
            "6": {"name": "Blacklist Pro Check", "desc": "Verificación profesional de lista negra", "popular": True, "credits": 1},
            "10": {"name": "IMEI to Model [All Brands]", "desc": "Identificar modelo por IMEI", "popular": True, "credits": 1},
            "11": {"name": "IMEI to Brand/Model/Name", "desc": "Marca y modelo por IMEI", "credits": 1},
            "14": {"name": "IMEI to SN Converter", "desc": "Convertir IMEI a número de serie", "credits": 1},
            "55": {"name": "Blacklist Status (Económico)", "desc": "Verificación básica de lista negra", "credits": 1},
            "62": {"name": "EID INFO (IMEI TO EID)", "desc": "Obtener EID desde IMEI", "credits": 1}
        }
    },
    "carriers": {
        "name": "📶 Operadoras",
        "emoji": "📶",
        "description": "Verificaciones específicas de operadoras",
        "services": {
            "15": {"name": "T-Mobile (ESN) PRO Check", "desc": "Verificación T-Mobile", "popular": True, "credits": 2},
            "16": {"name": "Verizon Clean/Lost Status", "desc": "Estado Verizon", "popular": True, "credits": 2}
        }
    },
    "others": {
        "name": "📲 Otras Marcas",
        "emoji": "📲", 
        "description": "Servicios para Xiaomi, OnePlus, Huawei, etc.",
        "services": {
            "17": {"name": "Huawei IMEI Info", "desc": "Información Huawei", "credits": 1},
            "25": {"name": "Xiaomi MI LOCK & INFO", "desc": "Estado Mi Account y info", "credits": 1},
            "27": {"name": "OnePlus IMEI INFO", "desc": "Información OnePlus", "credits": 1},
            "57": {"name": "Google Pixel Info", "desc": "Información Google Pixel", "credits": 1},
            "58": {"name": "Honor Info", "desc": "Información Honor", "credits": 1},
            "59": {"name": "Realme Info", "desc": "Información Realme", "credits": 1},
            "60": {"name": "Oppo Info", "desc": "Información Oppo", "credits": 1},
            "63": {"name": "Motorola Info", "desc": "Información Motorola", "credits": 1}
        }
    }
}

# Variables globales para datos en memoria
user_data = {}
user_stats = {"total_queries": 0, "successful_queries": 0}

# =================== FUNCIONES DE GESTIÓN DE DATOS JSON ===================

def load_json_data(filename, default_data=None):
    """Cargar datos desde archivo JSON"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return default_data if default_data is not None else {}
    except Exception as e:
        logger.error(f"Error cargando {filename}: {e}")
        return default_data if default_data is not None else {}

def save_json_data(filename, data):
    """Guardar datos en archivo JSON"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error guardando {filename}: {e}")
        return False

def init_data_files():
    """Inicializar archivos de datos JSON"""
    # Cargar usuarios autorizados desde archivo
    auth_data = load_json_data(DATA_FILES["auth"], AUTHORIZED_USERS)
    
    # Si el archivo no existe, crearlo con los datos por defecto
    if not os.path.exists(DATA_FILES["auth"]):
        save_json_data(DATA_FILES["auth"], AUTHORIZED_USERS)
    
    # Cargar estadísticas del bot
    stats_data = load_json_data(DATA_FILES["stats"], {
        "total_queries": 0,
        "successful_queries": 0,
        "failed_queries": 0,
        "error_queries": 0,
        "start_date": datetime.now(timezone.utc).isoformat(),
        "last_update": datetime.now(timezone.utc).isoformat()
    })
    
    # Actualizar estadísticas globales
    global user_stats
    user_stats.update(stats_data)
    
    logger.info("Archivos de datos inicializados correctamente")

def get_authorized_users():
    """Obtener lista de usuarios autorizados actualizada"""
    return load_json_data(DATA_FILES["auth"], AUTHORIZED_USERS)

def update_user_credits(user_id, credits_used):
    """Actualizar créditos de usuario"""
    auth_users = get_authorized_users()
    
    if user_id in auth_users:
        user_info = auth_users[user_id]
        if user_info.get("credits", 0) != -1:  # -1 = ilimitado
            user_info["credits"] = max(0, user_info.get("credits", 0) - credits_used)
            auth_users[user_id] = user_info
            save_json_data(DATA_FILES["auth"], auth_users)
        return True
    return False

def log_query(user_id, username, service_id, service_name, imei_sn, status, result_data=None, error_msg=None):
    """Registrar consulta en archivo JSON"""
    try:
        # Cargar log existente
        queries_log = load_json_data(DATA_FILES["queries"], [])
        
        # Crear entrada de log
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "username": username,
            "service_id": service_id,
            "service_name": service_name,
            "imei_sn_masked": mask_sensitive_data(imei_sn),
            "imei_sn_full": imei_sn,  # Guardamos completo para admins
            "status": status,  # success, failed, error
            "result_preview": str(result_data)[:200] if result_data else None,
            "error_message": error_msg,
            "credits_used": get_service_credits(service_id)
        }
        
        # Agregar al log
        queries_log.append(log_entry)
        
        # Mantener solo los últimos 1000 registros
        if len(queries_log) > 1000:
            queries_log = queries_log[-1000:]
        
        # Guardar log actualizado
        save_json_data(DATA_FILES["queries"], queries_log)
        
        logger.info(f"Consulta registrada: Usuario {user_id}, Servicio {service_id}, Status {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error registrando consulta: {e}")
        return False

def update_bot_stats(status):
    """Actualizar estadísticas del bot"""
    try:
        global user_stats
        
        user_stats["total_queries"] += 1
        
        if status == "success":
            user_stats["successful_queries"] += 1
        elif status == "failed":
            user_stats["failed_queries"] = user_stats.get("failed_queries", 0) + 1
        elif status == "error":
            user_stats["error_queries"] = user_stats.get("error_queries", 0) + 1
        
        user_stats["last_update"] = datetime.now(timezone.utc).isoformat()
        
        # Guardar en archivo
        save_json_data(DATA_FILES["stats"], user_stats)
        
    except Exception as e:
        logger.error(f"Error actualizando estadísticas: {e}")

def mask_sensitive_data(data):
    """Enmascarar datos sensibles para logs"""
    if len(data) > 8:
        return data[:4] + "***" + data[-3:]
    else:
        return data[:2] + "***"

def get_service_credits(service_id):
    """Obtener créditos requeridos para un servicio"""
    for category in SERVICES.values():
        if service_id in category["services"]:
            return category["services"][service_id].get("credits", 1)
    return 1

# =================== FUNCIONES DE AUTORIZACIÓN ===================

def is_authorized(user_id):
    """Verificar si un usuario está autorizado"""
    auth_users = get_authorized_users()
    return user_id in auth_users

def get_user_info(user_id):
    """Obtener información del usuario autorizado"""
    auth_users = get_authorized_users()
    return auth_users.get(user_id, None)

def has_credits(user_id, required_credits):
    """Verificar si el usuario tiene créditos suficientes"""
    user_info = get_user_info(user_id)
    if not user_info:
        return False
    
    user_credits = user_info.get("credits", 0)
    return user_credits == -1 or user_credits >= required_credits  # -1 = ilimitado

def create_unauthorized_message():
    """Crear mensaje para usuarios no autorizados"""
    return """
🚫 **ACCESO NO AUTORIZADO**

Lo siento, este bot es de **uso exclusivo** para usuarios autorizados.

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   **¿CÓMO OBTENER ACCESO?**                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

💰 **Planes Disponibles:**
• 🥉 **Básico**: 50 consultas - $10 USD
• 🥈 **Premium**: 200 consultas - $30 USD  
• 🥇 **Pro**: 500 consultas - $60 USD
• 💎 **Unlimited**: Consultas ilimitadas - $100 USD

🎯 **Beneficios:**
✅ Acceso a +60 servicios premium
✅ Resultados en tiempo real
✅ Soporte técnico 24/7
✅ Datos seguros y confiables

📞 **Contacto para activación:**
👨‍💻 **Admin**: @tu_usuario_admin
💬 **Telegram**: t.me/tu_canal_soporte
🌐 **Web**: tu-sitio-web.com

🔐 **Tu ID de usuario:** `{}`

*Proporciona este ID al administrador para activar tu cuenta*
    """

# =================== FUNCIONES DE MENÚS ===================

def create_main_menu():
    """Crear el menú principal mejorado"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for category_key, category_info in SERVICES.items():
        service_count = len(category_info["services"])
        popular_count = len([s for s in category_info["services"].values() if s.get("popular", False)])
        
        btn_text = f"{category_info['emoji']} {category_info['name']}"
        if popular_count > 0:
            btn_text += f" ⭐"
        btn_text += f" ({service_count})"
        
        btn = types.InlineKeyboardButton(
            btn_text,
            callback_data=f"cat_{category_key}"
        )
        markup.add(btn)
    
    markup.add(types.InlineKeyboardButton("━━━━━━━━━━━━━━━━━━━━", callback_data="separator"))
    
    markup.add(
        types.InlineKeyboardButton("⭐ Servicios Populares", callback_data="popular"),
        types.InlineKeyboardButton("💳 Mis Créditos", callback_data="credits")
    )
    
    markup.add(
        types.InlineKeyboardButton("ℹ️ Ayuda", callback_data="help"),
        types.InlineKeyboardButton("📊 Estadísticas", callback_data="stats")
    )
    
    return markup

def create_main_menu_button():
    """Crear solo el botón de menú principal"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏠 Menú Principal", callback_data="main_menu"))
    return markup

def create_category_menu(category_key):
    """Crear menú de categoría mejorado"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    category_info = SERVICES[category_key]
    
    popular_services = []
    regular_services = []
    
    for service_id, service_info in category_info["services"].items():
        if service_info.get("popular", False):
            popular_services.append((service_id, service_info))
        else:
            regular_services.append((service_id, service_info))
    
    if popular_services:
        markup.add(types.InlineKeyboardButton("⭐ SERVICIOS POPULARES", callback_data="separator"))
        for service_id, service_info in popular_services:
            credits = service_info.get("credits", 1)
            btn_text = f"⭐ {service_info['name']} ({credits}💳)"
            btn = types.InlineKeyboardButton(btn_text, callback_data=f"svc_{service_id}")
            markup.add(btn)
    
    if regular_services:
        if popular_services:
            markup.add(types.InlineKeyboardButton("📋 OTROS SERVICIOS", callback_data="separator"))
        
        for service_id, service_info in regular_services:
            credits = service_info.get("credits", 1)
            btn_text = f"• {service_info['name']} ({credits}💳)"
            btn = types.InlineKeyboardButton(btn_text, callback_data=f"svc_{service_id}")
            markup.add(btn)
    
    markup.add(types.InlineKeyboardButton("━━━━━━━━━━━━━━━━━━━━", callback_data="separator"))
    markup.add(
        types.InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu"),
        types.InlineKeyboardButton("💳 Mis Créditos", callback_data="credits")
    )
    
    return markup

def create_popular_menu():
    """Crear menú de servicios populares"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    popular_services = []
    for category_key, category_info in SERVICES.items():
        for service_id, service_info in category_info["services"].items():
            if service_info.get("popular", False):
                popular_services.append((service_id, service_info, category_info["emoji"]))
    
    markup.add(types.InlineKeyboardButton("⭐ SERVICIOS MÁS UTILIZADOS", callback_data="separator"))
    
    for service_id, service_info, emoji in popular_services:
        credits = service_info.get("credits", 1)
        btn_text = f"{emoji} {service_info['name']} ({credits}💳)"
        btn = types.InlineKeyboardButton(btn_text, callback_data=f"svc_{service_id}")
        markup.add(btn)
    
    markup.add(types.InlineKeyboardButton("━━━━━━━━━━━━━━━━━━━━", callback_data="separator"))
    markup.add(types.InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu"))
    
    return markup

def create_service_confirmation_menu(service_id):
    """Crear menú de confirmación de servicio"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("✅ Continuar", callback_data=f"confirm_{service_id}"),
        types.InlineKeyboardButton("🔙 Cambiar", callback_data="main_menu")
    )
    
    markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data="cancel"))
    
    return markup

# =================== HANDLERS DE COMANDOS ===================

@bot.message_handler(commands=['start'])
def start_command(message):
    """Comando de inicio con verificación de autorización"""
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    
    if not is_authorized(user_id):
        unauthorized_text = create_unauthorized_message().format(user_id)
        bot.send_message(message.chat.id, unauthorized_text, parse_mode='Markdown')
        logger.warning(f"Acceso no autorizado: Usuario {user_id} (@{message.from_user.username})")
        return
    
    user_info = get_user_info(user_id)
    credits = user_info.get("credits", 0)
    credits_text = "Ilimitados" if credits == -1 else str(credits)
    
    welcome_text = f"""
🤖 **¡Bienvenido {username}!**

**DEVICE CHECKER BOT** 🔍
*Tu asistente profesional para verificación de dispositivos*

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  👤 **Usuario:** {user_info.get('name', 'Usuario')}       ┃
┃  🏷️ **Plan:** {user_info.get('role', 'Usuario').title()}              ┃  
┃  💳 **Créditos:** {credits_text}                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

🎯 **ESPECIALIDADES:**
• **🍎 Apple**: FMI, iCloud, GSX, Garantía
• **📱 Samsung**: Knox, Blacklist, Info completa  
• **🌐 Universal**: GSMA, IMEI Info, Modelos
• **📶 Carriers**: T-Mobile, Verizon checks
• **📲 Otras marcas**: 15+ marcas soportadas

💡 **PROCESO SIMPLE:**
1️⃣ Selecciona tu categoría favorita
2️⃣ Elige el servicio específico  
3️⃣ Envía IMEI o Serial Number
4️⃣ ¡Obtén información detallada!

🔥 **¡Comienza ahora!** 👇
    """
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=create_main_menu()
    )

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Mostrar estadísticas del bot para usuarios autorizados"""
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        bot.reply_to(message, "❌ No tienes permisos para ver las estadísticas.")
        return
    
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    success_rate = (user_stats["successful_queries"] / max(user_stats["total_queries"], 1)) * 100
    
    user_info = get_user_info(user_id)
    
    stats_text = f"""
📊 **ESTADÍSTICAS DEL BOT**

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    **TU CUENTA**                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

👤 **Usuario:** {user_info.get('name', 'Usuario')}
🏷️ **Plan:** {user_info.get('role', 'Usuario').title()}
💳 **Créditos restantes:** {"Ilimitados" if user_info.get('credits') == -1 else user_info.get('credits', 0)}

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   **ESTADÍSTICAS GENERALES**          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📈 **Consultas Totales:** {user_stats['total_queries']:,}
✅ **Consultas Exitosas:** {user_stats['successful_queries']:,}
❌ **Consultas Fallidas:** {user_stats.get('failed_queries', 0):,}
🚫 **Errores del Sistema:** {user_stats.get('error_queries', 0):,}
📊 **Tasa de Éxito:** {success_rate:.1f}%

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                  **ESTADO DEL SISTEMA**               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

🟢 **Estado:** Activo y Operativo
⚡ **Uptime:** 24/7 Disponible
🌐 **API Status:** ✅ Conectado
🛡️ **Usuarios Activos:** {len(get_authorized_users())}

**📅 Última actualización:** {current_time}
    """
    
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

# =================== HANDLERS DE CALLBACKS ===================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Manejar callbacks con verificación de autorización"""
    try:
        user_id = call.from_user.id
        data = call.data
        
        # Verificar autorización para todos los callbacks
        if not is_authorized(user_id):
            bot.answer_callback_query(call.id, "❌ Acceso no autorizado")
            return
        
        # Ignorar separadores
        if data == "separator":
            bot.answer_callback_query(call.id)
            return
        
        if data == "main_menu":
            edit_message_with_menu(call, "🏠 **MENÚ PRINCIPAL**\n\nSelecciona una categoría para continuar:", create_main_menu())
            
        elif data.startswith("cat_"):
            category_key = data.replace("cat_", "")
            if category_key in SERVICES:
                category_info = SERVICES[category_key]
                header_text = f"{category_info['emoji']} **{category_info['name'].upper()}**\n\n"
                header_text += f"*{category_info['description']}*\n\n"
                header_text += f"**Servicios disponibles:** {len(category_info['services'])}\n"
                header_text += "💳 = Créditos requeridos\n\n"
                header_text += "Selecciona el servicio que necesitas:"
                
                edit_message_with_menu(call, header_text, create_category_menu(category_key))
        
        elif data == "popular":
            header_text = "⭐ **SERVICIOS POPULARES**\n\n"
            header_text += "*Los servicios más utilizados y recomendados*\n\n"
            header_text += "💳 = Créditos requeridos\n\n"
            header_text += "Estos servicios ofrecen la mejor relación calidad-precio:"
            
            edit_message_with_menu(call, header_text, create_popular_menu())
        
        elif data.startswith("svc_"):
            service_id = data.replace("svc_", "")
            show_service_info(call, service_id)
        
        elif data.startswith("confirm_"):
            service_id = data.replace("confirm_", "")
            confirm_service_selection(call, service_id)
        
        elif data == "credits":
            show_credits_info(call)
        
        elif data == "help":
            help_command(call.message)
        
        elif data == "stats":
            stats_command(call.message)
        
        elif data == "cancel":
            cancel_operation(call)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error en callback_handler: {e}")
        bot.answer_callback_query(call.id, "❌ Error procesando solicitud")

def show_credits_info(call):
    """Mostrar información de créditos del usuario"""
    user_id = call.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info:
        bot.answer_callback_query(call.id, "❌ Error obteniendo información")
        return
    
    credits = user_info.get("credits", 0)
    
    credits_text = f"""
💳 **INFORMACIÓN DE CRÉDITOS**

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    **TU CUENTA**                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

👤 **Usuario:** {user_info.get('name', 'Usuario')}
🏷️ **Plan:** {user_info.get('role', 'Usuario').title()}
💎 **Créditos disponibles:** {"♾️ Ilimitados" if credits == -1 else f"{credits} créditos"}

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                  **COSTO POR SERVICIO**               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

💰 **Servicios básicos:** 1 crédito
⚡ **Servicios premium:** 2-3 créditos  
🌟 **Servicios avanzados:** 4+ créditos

💡 **Consejos:**
• Los servicios populares (⭐) suelen ser más económicos
• Los servicios Apple GSX requieren más créditos
• Verifica siempre el costo antes de confirmar

📞 **¿Necesitas más créditos?**
Contacta al administrador: @admin_username

🔄 **Historial de uso disponible para administradores**
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu"))
    
    edit_message_with_menu(call, credits_text, markup)

def edit_message_with_menu(call, text, markup):
    """Editar mensaje con nuevo menú"""
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Error editando mensaje: {e}")

def show_service_info(call, service_id):
    """Mostrar información detallada del servicio con verificación de créditos"""
    user_id = call.from_user.id
    
    # Buscar el servicio en todas las categorías
    service_info = None
    category_info = None
    
    for cat_key, cat_data in SERVICES.items():
        if service_id in cat_data["services"]:
            service_info = cat_data["services"][service_id]
            category_info = cat_data
            break
    
    if not service_info:
        bot.answer_callback_query(call.id, "❌ Servicio no encontrado")
        return
    
    # Verificar créditos
    required_credits = service_info.get("credits", 1)
    user_has_credits = has_credits(user_id, required_credits)
    
    popular_badge = "⭐ " if service_info.get("popular", False) else ""
    credits_status = "✅" if user_has_credits else "❌"
    
    info_text = f"""
{category_info['emoji']} **INFORMACIÓN DEL SERVICIO**

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  {popular_badge}**{service_info['name']}**
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📋 **Descripción:**
{service_info.get('desc', 'Servicio de verificación profesional')}

🏷️ **Categoría:** {category_info['name']}
🆔 **ID de Servicio:** {service_id}
💳 **Costo:** {required_credits} crédito(s)
{credits_status} **Estado:** {"Puedes usar este servicio" if user_has_credits else "Créditos insuficientes"}

{"⭐ **Popular:** Servicio más utilizado" if service_info.get('popular', False) else ""}

💡 **Qué necesitas:**
• IMEI válido (15 dígitos) o Serial Number
• Dispositivo debe estar registrado en bases de datos
• Conexión a internet estable

⏱️ **Tiempo estimado:** 15-60 segundos
🔐 **Seguridad:** Datos procesados de forma segura

{"¿Deseas continuar con este servicio?" if user_has_credits else "Contacta al admin para obtener más créditos."}
    """
    
    if user_has_credits:
        markup = create_service_confirmation_menu(service_id)
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu"))
    
    edit_message_with_menu(call, info_text, markup)

def confirm_service_selection(call, service_id):
    """Confirmar selección de servicio y solicitar IMEI"""
    user_id = call.from_user.id
    
    # Verificar créditos nuevamente
    required_credits = get_service_credits(service_id)
    if not has_credits(user_id, required_credits):
        bot.answer_callback_query(call.id, "❌ Créditos insuficientes")
        return
    
    # Buscar información del servicio
    service_info = None
    category_info = None
    
    for cat_key, cat_data in SERVICES.items():
        if service_id in cat_data["services"]:
            service_info = cat_data["services"][service_id]
            category_info = cat_data
            break
    
    if not service_info:
        bot.answer_callback_query(call.id, "❌ Servicio no encontrado")
        return
    
    # Guardar selección del usuario
    user_data[user_id] = {
        'service_id': service_id,
        'service_name': service_info['name'],
        'category': category_info['name'],
        'waiting_for_imei': True,
        'timestamp': time.time(),
        'credits_required': required_credits
    }
    
    confirmation_text = f"""
✅ **SERVICIO SELECCIONADO**

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  **{service_info['name']}**
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

🏷️ **Categoría:** {category_info['name']}
🆔 **Servicio ID:** {service_id}
💳 **Costo:** {required_credits} crédito(s)

📝 **SIGUIENTE PASO:**
Envía el **IMEI** o **Serial Number** del dispositivo

💡 **FORMATOS VÁLIDOS:**

🔹 **IMEI (15 dígitos):**
   `359111099999999`
   `867839040123456`

🔹 **Serial Number Apple:**
   `F17QW0QAHC6L`
   `DMQVGC9MQ05N`

🔹 **MEID (14 dígitos hex):**
   `A1000012345678`

⚠️ **IMPORTANTE:**
• Solo números y letras, sin espacios ni guiones
• Verifica que el código sea correcto antes de enviar
• Se debitarán {required_credits} crédito(s) al procesar
• Para cancelar, usa el comando /cancel

🔄 **Esperando tu IMEI/Serial...**
    """
    
    bot.edit_message_text(
        confirmation_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

def cancel_operation(call):
    """Cancelar operación actual"""
    user_id = call.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    cancel_text = """
❌ **OPERACIÓN CANCELADA**

La operación actual ha sido cancelada exitosamente.
No se han debitado créditos de tu cuenta.

¿En qué puedo ayudarte ahora?
    """
    
    edit_message_with_menu(call, cancel_text, create_main_menu())

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    """Comando para cancelar operación"""
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        bot.reply_to(message, "❌ Acceso no autorizado.")
        return
    
    if user_id in user_data:
        del user_data[user_id]
    
    cancel_text = """
❌ **OPERACIÓN CANCELADA**

Tu consulta actual ha sido cancelada.
No se han debitado créditos de tu cuenta.

¡Estoy aquí para ayudarte! 🤖
    """
    
    bot.send_message(
        message.chat.id,
        cancel_text,
        parse_mode='Markdown',
        reply_markup=create_main_menu()
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    """Comando de ayuda para usuarios autorizados"""
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        bot.reply_to(message, "❌ Acceso no autorizado.")
        return
    
    help_text = """
🆘 **GUÍA COMPLETA - Device Checker Bot**

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    **COMANDOS DISPONIBLES**                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

🔸 `/start` - Mostrar menú principal
🔸 `/help` - Mostrar esta guía completa
🔸 `/stats` - Ver estadísticas personalizadas
🔸 `/cancel` - Cancelar operación actual
🔸 `/credits` - Ver información de créditos

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   **SISTEMA DE CRÉDITOS**                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

💳 **Cada consulta consume créditos según el servicio:**
• 💰 Servicios básicos: 1 crédito
• ⚡ Servicios premium: 2-3 créditos
• 🌟 Servicios avanzados: 4+ créditos

💡 **Los créditos se debitan solo si la consulta es exitosa**

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   **FORMATOS SOPORTADOS**                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📱 **IMEI** (15 dígitos): `359111099999999`
🔢 **Serial Apple**: `F17QW0QAHC6L`
📋 **MEID** (14 hex): `A1000012345678`

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    **SOPORTE TÉCNICO**                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

🔧 **Problemas comunes:**
• Verificar formato IMEI/SN correcto
• Esperar 30-60 segundos para resultados
• Verificar que tengas créditos suficientes

📞 **Contacto:** @admin_username
🆔 **Tu ID:** `{message.from_user.id}`
    """
    
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['credits'])
def credits_command(message):
    """Comando para ver créditos del usuario"""
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        bot.reply_to(message, "❌ Acceso no autorizado.")
        return
    
    user_info = get_user_info(user_id)
    credits = user_info.get("credits", 0)
    
    credits_text = f"""
💳 **TUS CRÉDITOS**

👤 **Usuario:** {user_info.get('name', 'Usuario')}
🏷️ **Plan:** {user_info.get('role', 'Usuario').title()}
💎 **Créditos disponibles:** {"♾️ Ilimitados" if credits == -1 else f"{credits} créditos"}

💰 **Costo por servicio:**
• Básicos: 1 crédito
• Premium: 2-3 créditos  
• Avanzados: 4+ créditos

📞 **¿Necesitas recargar?** Contacta: @admin_username
    """
    
    bot.reply_to(message, credits_text, parse_mode='Markdown')

# =================== HANDLER DE MENSAJES PRINCIPALES ===================

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Manejar mensajes de texto con autorización"""
    try:
        user_id = message.from_user.id
        text = message.text.strip()
        
        # Verificar autorización
        if not is_authorized(user_id):
            unauthorized_text = create_unauthorized_message().format(user_id)
            bot.reply_to(message, unauthorized_text, parse_mode='Markdown')
            return
        
        # Verificar si el usuario está esperando un IMEI/SN
        if user_id in user_data and user_data[user_id].get('waiting_for_imei'):
            
            # Validación del formato
            validation_result = validate_imei_serial(text)
            
            if not validation_result["valid"]:
                error_text = f"""
❌ **FORMATO INVÁLIDO**

**Error detectado:** {validation_result['error']}

💡 **FORMATOS CORRECTOS:**

🔹 **IMEI (15 dígitos):** `359111099999999`
🔹 **Serial Apple:** `F17QW0QAHC6L`  
🔹 **MEID (14 hex):** `A1000012345678`

🔄 **Intenta nuevamente o usa /cancel para salir**
                """
                
                bot.reply_to(message, error_text, parse_mode='Markdown')
                return
            
            # Procesar consulta si el formato es válido
            process_device_check_enhanced(message, user_id, text)
            
        else:
            # Mensaje no reconocido - respuesta amigable
            help_text = """
🤖 **¡Hola! No reconozco ese comando**

Para usar el bot correctamente:

🔸 **Usa /start** - Para ver el menú principal
🔸 **Usa /help** - Para obtener ayuda detallada  
🔸 **Usa /credits** - Para ver tus créditos

¡Comencemos! 👇
            """
            
            bot.reply_to(
                message,
                help_text,
                parse_mode='Markdown',
                reply_markup=create_main_menu()
            )
            
    except Exception as e:
        logger.error(f"Error en handle_message: {e}")
        bot.reply_to(
            message, 
            "❌ **Error inesperado**\n\nHa ocurrido un error. Por favor intenta de nuevo con /start",
            parse_mode='Markdown'
        )

# =================== FUNCIONES DE PROCESAMIENTO ===================

def validate_imei_serial(text):
    """Validar formato de IMEI/Serial con mensajes específicos"""
    text = re.sub(r'[^A-Za-z0-9]', '', text)
    
    if len(text) < 8:
        return {"valid": False, "error": "Muy corto (mínimo 8 caracteres)"}
    
    if len(text) > 20:
        return {"valid": False, "error": "Muy largo (máximo 20 caracteres)"}
    
    if len(text) == 15 and text.isdigit():
        return {"valid": True, "type": "IMEI", "cleaned": text}
    
    if 8 <= len(text) <= 12 and text.isalnum():
        return {"valid": True, "type": "Serial", "cleaned": text}
    
    if len(text) == 14 and all(c in '0123456789ABCDEF' for c in text.upper()):
        return {"valid": True, "type": "MEID", "cleaned": text.upper()}
    
    if text.isalnum() and 10 <= len(text) <= 17:
        return {"valid": True, "type": "Unknown", "cleaned": text}
    
    return {"valid": False, "error": "Formato no reconocido (solo letras y números)"}

def process_device_check_enhanced(message, user_id, imei_sn):
    """Procesar verificación con autorización y registro"""
    try:
        user_info_data = user_data[user_id]
        service_id = user_info_data['service_id']
        service_name = user_info_data['service_name']
        category = user_info_data['category']
        credits_required = user_info_data['credits_required']
        
        username = message.from_user.username or message.from_user.first_name
        
        # Verificar créditos una vez más antes de procesar
        if not has_credits(user_id, credits_required):
            bot.reply_to(message, "❌ **Créditos insuficientes**\n\nNo tienes suficientes créditos para este servicio.", parse_mode='Markdown')
            if user_id in user_data:
                del user_data[user_id]
            return
        
        # Mensaje de procesamiento
        processing_text = f"""
⏳ **PROCESANDO CONSULTA...**

**📋 Servicio:** {service_name}
**🔍 IMEI/SN:** `{imei_sn}`
**💳 Costo:** {credits_required} crédito(s)

🔄 Consultando base de datos...
⏱️ Tiempo estimado: 15-30 segundos

*Por favor espera...*
        """
        
        processing_msg = bot.reply_to(message, processing_text, parse_mode='Markdown')
        
        # Realizar consulta a la API
        result = make_api_request_enhanced(service_id, imei_sn)
        
        # Procesar respuesta y actualizar créditos solo si es exitosa
        if result['status'] == 'success':
            # Debitar créditos solo en caso de éxito
            update_user_credits(user_id, credits_required)
            update_bot_stats('success')
            
            response_text = format_success_response_premium(service_name, category, imei_sn, result['data'])
            log_query(user_id, username, service_id, service_name, imei_sn, 'success', result['data'])
            
        elif result['status'] == 'failed':
            # No debitar créditos en caso de fallo
            update_bot_stats('failed')
            response_text = format_failed_response_enhanced(service_name, category, imei_sn, result.get('message', 'Consulta falló'))
            log_query(user_id, username, service_id, service_name, imei_sn, 'failed', error_msg=result.get('message'))
            
        else:
            # No debitar créditos en caso de error
            update_bot_stats('error')
            response_text = format_error_response_enhanced(service_name, category, imei_sn, result.get('error', 'Error desconocido'))
            log_query(user_id, username, service_id, service_name, imei_sn, 'error', error_msg=result.get('error'))
        
        # Enviar resultado final
        bot.send_message(
            processing_msg.chat.id,
            response_text,
            parse_mode='Markdown',
            reply_markup=create_main_menu_button()
        )
        
        # Limpiar datos del usuario
        if user_id in user_data:
            del user_data[user_id]
            
    except Exception as e:
        logger.error(f"Error en process_device_check_enhanced: {e}")
        error_text = f"""
🚫 **ERROR CRÍTICO**

Ha ocurrido un error inesperado al procesar tu consulta.
No se han debitado créditos de tu cuenta.

**¿Qué puedes hacer?**
• Intenta nuevamente en unos minutos
• Verifica que el IMEI/SN sea correcto
• Usa /cancel para salir y comenzar de nuevo

¡Disculpas por las molestias! 🙏
        """
        
        bot.reply_to(message, error_text, parse_mode='Markdown')

def make_api_request_enhanced(service_id, imei_sn):
    """Realizar solicitud a la API con mejor manejo de errores"""
    try:
        url = f"{API_ENDPOINT}?key={API_KEY}&service={service_id}&imei={imei_sn}"
        logger.info(f"Realizando consulta API: Service {service_id}, IMEI: {imei_sn[:8]}...")
        
        headers = {
            'User-Agent': 'DeviceCheckerBot/2.0',
            'Accept': 'application/json, text/html',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(url, headers=headers, timeout=45)
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.info(f"Respuesta JSON exitosa para servicio {service_id}")
                return {'status': 'success', 'data': data}
            except json.JSONDecodeError:
                logger.info(f"Respuesta HTML/texto para servicio {service_id}")
                return {'status': 'success', 'data': {'result': response.text}}
        elif response.status_code == 404:
            return {'status': 'failed', 'message': 'Servicio no disponible temporalmente'}
        elif response.status_code == 429:
            return {'status': 'failed', 'message': 'Demasiadas consultas, intenta en unos minutos'}
        elif response.status_code == 403:
            return {'status': 'failed', 'message': 'API Key inválida o sin créditos'}
        else:
            return {'status': 'failed', 'message': f'Error HTTP {response.status_code}'}
            
    except requests.exceptions.Timeout:
        logger.error("Timeout en API request")
        return {'status': 'error', 'error': 'Tiempo de espera agotado (>45s)'}
    except requests.exceptions.ConnectionError:
        logger.error("Error de conexión a API")
        return {'status': 'error', 'error': 'Error de conexión con el servidor'}
    except Exception as e:
        logger.error(f"Error inesperado en API: {e}")
        return {'status': 'error', 'error': f'Error inesperado: {str(e)[:50]}...'}

def parse_html_result_enhanced(html_content):
    """Parser HTML mejorado"""
    try:
        decoded_content = html.unescape(html_content)
        decoded_content = re.sub(r'<img[^>]*>', '', decoded_content)
        decoded_content = re.sub(r'<script[^>]*>.*?</script>', '', decoded_content, flags=re.DOTALL)
        decoded_content = re.sub(r'<style[^>]*>.*?</style>', '', decoded_content, flags=re.DOTALL)
        
        lines = decoded_content.split('<br>')
        parsed_data = {}
        
        for line in lines:
            line = line.strip()
            if ':' in line and line:
                clean_line = re.sub(r'<[^>]+>', '', line)
                clean_line = re.sub(r'\s+', ' ', clean_line).strip()
                
                if ':' in clean_line and len(clean_line) > 3:
                    parts = clean_line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        
                        if len(key) > 2 and len(value) > 0:
                            parsed_data[key] = value
        
        return parsed_data
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return {}

def format_success_response_premium(service_name, category, imei_sn, data):
    """Formatear respuesta exitosa"""
    response = f"✅ **CONSULTA EXITOSA**\n\n"
    response += f"**📋 Servicio:** {service_name}\n"
    response += f"**🔍 IMEI/SN:** `{imei_sn}`\n\n"
    
    if isinstance(data, dict) and 'result' in data:
        parsed_data = parse_html_result_enhanced(data['result'])
        if parsed_data:
            formatted_info = format_device_info_monospace(parsed_data)
            response += f"```\n{formatted_info}```"
        else:
            clean_result = clean_html_content(data['result'])
            response += f"```\n{clean_result}\n```"
    else:
        if isinstance(data, dict):
            response += "```\n"
            for key, value in data.items():
                if key.lower() not in ['status', 'success', 'result', 'order_id', 'credit', 'balance_left']:
                    response += f"{key}: {value}\n"
            response += "```"
        else:
            response += f"```\n{data}\n```"
    
    return response

def format_device_info_monospace(parsed_data):
    """Formatear información del dispositivo"""
    if not parsed_data:
        return "No se pudo extraer información del dispositivo"
    
    formatted_text = ""
    
    field_order = [
        "Model Description", "Model", "Brand", "IMEI", "IMEI Number", "IMEI2", "IMEI2 Number", 
        "MEID", "MEID Number", "Serial Number", "Network", "Color", "Storage", "Estimated Purchase Date",
        "Purchase Date", "Valid Purchase Date", "Warranty Status", "Activation Status", "Demo Unit",
        "Loaner Device", "Replaced Device", "Replaced by Apple", "Replacement Device", "Refurbished",
        "Refurbished Device", "Purchase Country", "Locked Carrier", "Carrier", "SIM-Lock Status",
        "Sim-Lock Status", "SimLock Status", "Find My iPhone", "FMI Status", "iCloud Status",
        "iCloud Clean/Lost", "US Block Status", "Blacklist Status", "GSMA Status"
    ]
    
    # Mostrar campos en el orden especificado
    shown_fields = set()
    
    for field in field_order:
        if field in parsed_data and field not in shown_fields:
            value = parsed_data[field]
            formatted_text += f"{field}: {value}\n"
            shown_fields.add(field)
    
    # Mostrar campos restantes que no estaban en el orden
    for field, value in parsed_data.items():
        if field not in shown_fields:
            formatted_text += f"{field}: {value}\n"
    
    return formatted_text.strip()

def clean_html_content(html_content):
    """Limpiar contenido HTML para mostrar como texto plano"""
    try:
        decoded = html.unescape(html_content)
        clean_text = re.sub(r'<[^>]+>', '', decoded)
        clean_text = clean_text.replace('<br>', '\n').replace('<BR>', '\n')
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        result = '\n'.join(lines)
        
        if len(result) > 1500:
            result = result[:1500] + "..."
        
        return result
        
    except Exception as e:
        logger.error(f"Error limpiando HTML: {e}")
        return str(html_content)[:500] + "..."

def format_failed_response_enhanced(service_name, category, imei_sn, message):
    """Formatear respuesta fallida"""
    response = f"❌ **CONSULTA FALLIDA**\n\n"
    response += f"**📋 Servicio:** {service_name}\n"
    response += f"**🔍 IMEI/SN:** `{imei_sn}`\n\n"
    response += f"**⚠️ Motivo:** {message}\n\n"
    response += f"**💡 Posibles causas:**\n"
    response += f"• IMEI/SN inválido o incorrecto\n"
    response += f"• Dispositivo no encontrado en base de datos\n"
    response += f"• Servicio temporalmente no disponible\n\n"
    response += f"**💳 Estado:** No se han debitado créditos\n"
    response += f"Verifica el IMEI/SN e intenta de nuevo."
    
    return response

def format_error_response_enhanced(service_name, category, imei_sn, error):
    """Formatear respuesta de error"""
    response = f"🚫 **ERROR DEL SISTEMA**\n\n"
    response += f"**📋 Servicio:** {service_name}\n"
    response += f"**🔍 IMEI/SN:** `{imei_sn}`\n\n"
    response += f"**❗ Error:** {error}\n\n"
    response += f"**🔧 Soluciones:**\n"
    response += f"• Intenta de nuevo en unos minutos\n"
    response += f"• Verifica tu conexión a internet\n"
    response += f"• Prueba con otro servicio\n\n"
    response += f"**💳 Estado:** No se han debitado créditos\n"
    response += f"¡Disculpas por las molestias!"
    
    return response

# =================== COMANDOS DE ADMINISTRACIÓN ===================

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Panel de administración (solo para admins)"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        bot.reply_to(message, "❌ Acceso denegado. Solo para administradores.")
        return
    
    admin_text = """
👑 **PANEL DE ADMINISTRACIÓN**

**Comandos disponibles:**

📊 `/adminstats` - Estadísticas completas del sistema
👥 `/listusers` - Lista de usuarios autorizados  
➕ `/adduser <user_id> <role> <credits> <name>` - Agregar usuario
➖ `/removeuser <user_id>` - Eliminar usuario
💳 `/addcredits <user_id> <credits>` - Agregar créditos
📋 `/querylogs` - Ver últimas 10 consultas
🔄 `/backup` - Respaldar datos JSON

**Roles disponibles:** admin, premium, user
**Créditos:** Usar -1 para ilimitados

**Ejemplo:**
`/adduser 123456789 premium 100 Juan Pérez`
    """
    
    bot.reply_to(message, admin_text, parse_mode='Markdown')

@bot.message_handler(commands=['adminstats'])
def admin_stats_command(message):
    """Estadísticas completas para admins"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        bot.reply_to(message, "❌ Acceso denegado.")
        return
    
    auth_users = get_authorized_users()
    queries_log = load_json_data(DATA_FILES["queries"], [])
    
    # Estadísticas por rol
    role_stats = {}
    for uid, info in auth_users.items():
        role = info.get('role', 'user')
        if role not in role_stats:
            role_stats[role] = {'count': 0, 'total_credits': 0}
        role_stats[role]['count'] += 1
        credits = info.get('credits', 0)
        if credits != -1:
            role_stats[role]['total_credits'] += credits
    
    # Estadísticas de consultas recientes (últimas 24h)
    now = datetime.now(timezone.utc)
    recent_queries = [q for q in queries_log if 
                     (now - datetime.fromisoformat(q['timestamp'].replace('Z', '+00:00'))).days < 1]
    
    stats_text = f"""
👑 **ESTADÍSTICAS DE ADMINISTRADOR**

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    **USUARIOS ACTIVOS**                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

👥 **Total de usuarios:** {len(auth_users)}
"""
    
    for role, stats in role_stats.items():
        stats_text += f"• **{role.title()}:** {stats['count']} usuarios\n"
    
    stats_text += f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   **CONSULTAS GLOBALES**                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📈 **Total histórico:** {user_stats['total_queries']:,}
✅ **Exitosas:** {user_stats['successful_queries']:,}
❌ **Fallidas:** {user_stats.get('failed_queries', 0):,}
🚫 **Errores:** {user_stats.get('error_queries', 0):,}

📊 **Últimas 24h:** {len(recent_queries)} consultas
⚡ **Tasa de éxito:** {(user_stats['successful_queries'] / max(user_stats['total_queries'], 1) * 100):.1f}%

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   **SERVICIOS MÁS USADOS**               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""
    
    # Servicios más utilizados
    service_usage = {}
    for query in queries_log[-100:]:  # Últimas 100 consultas
        service = query.get('service_name', 'Unknown')
        service_usage[service] = service_usage.get(service, 0) + 1
    
    top_services = sorted(service_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    
    for i, (service, count) in enumerate(top_services, 1):
        stats_text += f"{i}. **{service}:** {count} usos\n"
    
    stats_text += f"\n**📅 Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    
    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['listusers'])
def list_users_command(message):
    """Listar usuarios autorizados (solo admins)"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        bot.reply_to(message, "❌ Acceso denegado.")
        return
    
    auth_users = get_authorized_users()
    
    users_text = "👥 **USUARIOS AUTORIZADOS**\n\n"
    
    for uid, info in auth_users.items():
        credits = "♾️" if info.get('credits') == -1 else str(info.get('credits', 0))
        users_text += f"**ID:** `{uid}`\n"
        users_text += f"**Nombre:** {info.get('name', 'Sin nombre')}\n"
        users_text += f"**Rol:** {info.get('role', 'user')}\n"
        users_text += f"**Créditos:** {credits}\n"
        users_text += "━━━━━━━━━━━━━━━━━━━━\n"
    
    bot.reply_to(message, users_text, parse_mode='Markdown')

@bot.message_handler(commands=['adduser'])
def add_user_command(message):
    """Agregar usuario autorizado (solo admins)"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        bot.reply_to(message, "❌ Acceso denegado.")
        return
    
    try:
        parts = message.text.split(' ', 4)
        if len(parts) < 5:
            bot.reply_to(message, "❌ **Uso:** `/adduser <user_id> <role> <credits> <name>`\n\n**Ejemplo:** `/adduser 123456789 premium 100 Juan Pérez`", parse_mode='Markdown')
            return
        
        new_user_id = int(parts[1])
        role = parts[2].lower()
        credits = int(parts[3])
        name = parts[4]
        
        if role not in ['admin', 'premium', 'user']:
            bot.reply_to(message, "❌ Rol inválido. Usa: admin, premium, user")
            return
        
        auth_users = get_authorized_users()
        auth_users[new_user_id] = {
            'role': role,
            'name': name,
            'credits': credits
        }
        
        if save_json_data(DATA_FILES["auth"], auth_users):
            bot.reply_to(message, f"✅ **Usuario agregado exitosamente**\n\n**ID:** {new_user_id}\n**Nombre:** {name}\n**Rol:** {role}\n**Créditos:** {credits}", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Error guardando usuario")
            
    except ValueError:
        bot.reply_to(message, "❌ ID de usuario y créditos deben ser números")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['removeuser'])
def remove_user_command(message):
    """Eliminar usuario autorizado (solo admins)"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        bot.reply_to(message, "❌ Acceso denegado.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ **Uso:** `/removeuser <user_id>`")
            return
        
        target_user_id = int(parts[1])
        auth_users = get_authorized_users()
        
        if target_user_id not in auth_users:
            bot.reply_to(message, "❌ Usuario no encontrado")
            return
        
        user_name = auth_users[target_user_id].get('name', 'Usuario')
        del auth_users[target_user_id]
        
        if save_json_data(DATA_FILES["auth"], auth_users):
            bot.reply_to(message, f"✅ **Usuario eliminado**\n\n**ID:** {target_user_id}\n**Nombre:** {user_name}")
        else:
            bot.reply_to(message, "❌ Error eliminando usuario")
            
    except ValueError:
        bot.reply_to(message, "❌ ID de usuario debe ser un número")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addcredits'])
def add_credits_command(message):
    """Agregar créditos a usuario (solo admins)"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        bot.reply_to(message, "❌ Acceso denegado.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ **Uso:** `/addcredits <user_id> <credits>`\n\n**Ejemplo:** `/addcredits 123456789 50`", parse_mode='Markdown')
            return
        
        target_user_id = int(parts[1])
        credits_to_add = int(parts[2])
        
        auth_users = get_authorized_users()
        
        if target_user_id not in auth_users:
            bot.reply_to(message, "❌ Usuario no encontrado")
            return
        
        current_credits = auth_users[target_user_id].get('credits', 0)
        
        if current_credits == -1:
            new_credits = -1  # Mantener ilimitado
        else:
            new_credits = current_credits + credits_to_add
        
        auth_users[target_user_id]['credits'] = new_credits
        
        if save_json_data(DATA_FILES["auth"], auth_users):
            user_name = auth_users[target_user_id].get('name', 'Usuario')
            credits_display = "Ilimitados" if new_credits == -1 else str(new_credits)
            bot.reply_to(message, f"✅ **Créditos agregados**\n\n**Usuario:** {user_name}\n**ID:** {target_user_id}\n**Créditos actuales:** {credits_display}")
        else:
            bot.reply_to(message, "❌ Error actualizando créditos")
            
    except ValueError:
        bot.reply_to(message, "❌ ID y créditos deben ser números")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['querylogs'])
def query_logs_command(message):
    """Ver logs de consultas (solo admins)"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        bot.reply_to(message, "❌ Acceso denegado.")
        return
    
    queries_log = load_json_data(DATA_FILES["queries"], [])
    
    if not queries_log:
        bot.reply_to(message, "📋 No hay consultas registradas")
        return
    
    logs_text = "📋 **ÚLTIMAS 10 CONSULTAS**\n\n"
    
    for query in queries_log[-10:]:
        timestamp = datetime.fromisoformat(query['timestamp'].replace('Z', '+00:00'))
        formatted_time = timestamp.strftime('%d/%m %H:%M')
        
        status_emoji = {"success": "✅", "failed": "❌", "error": "🚫"}.get(query['status'], "❓")
        
        logs_text += f"**{formatted_time}** {status_emoji}\n"
        logs_text += f"**Usuario:** {query['username']} (`{query['user_id']}`)\n"
        logs_text += f"**Servicio:** {query['service_name']}\n"
        logs_text += f"**IMEI:** {query['imei_sn_masked']}\n"
        logs_text += f"**Estado:** {query['status']}\n"
        
        if query.get('error_message'):
            logs_text += f"**Error:** {query['error_message'][:50]}...\n"
        
        logs_text += "━━━━━━━━━━━━━━━━━━━━\n"
    
    bot.reply_to(message, logs_text, parse_mode='Markdown')

@bot.message_handler(commands=['backup'])
def backup_command(message):
    """Crear respaldo de datos (solo admins)"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info or user_info.get('role') != 'admin':
        bot.reply_to(message, "❌ Acceso denegado.")
        return
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_data = {
            'timestamp': timestamp,
            'authorized_users': load_json_data(DATA_FILES["auth"], {}),
            'bot_stats': load_json_data(DATA_FILES["stats"], {}),
            'recent_queries': load_json_data(DATA_FILES["queries"], [])[-50:]  # Últimas 50
        }
        
        backup_filename = f"bot_backup_{timestamp}.json"
        
        if save_json_data(backup_filename, backup_data):
            backup_text = f"""
✅ **RESPALDO CREADO EXITOSAMENTE**

**📅 Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**📁 Archivo:** `{backup_filename}`

**📊 Contenido respaldado:**
• {len(backup_data['authorized_users'])} usuarios autorizados
• {len(backup_data['recent_queries'])} consultas recientes
• Estadísticas completas del sistema

**💾 El archivo se ha guardado en el servidor**
            """
            bot.reply_to(message, backup_text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Error creando respaldo")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# =================== FUNCIONES DE INICIALIZACIÓN Y EJECUCIÓN ===================

def setup_logging():
    """Configurar logging avanzado"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    file_handler = logging.FileHandler('device_checker_bot.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    requests_logger = logging.getLogger("requests")
    requests_logger.setLevel(logging.WARNING)

def cleanup_user_data():
    """Limpiar datos de usuario antiguos"""
    current_time = time.time()
    expired_users = []
    
    for user_id, data in user_data.items():
        if current_time - data.get('timestamp', 0) > 3600:  # 1 hora
            expired_users.append(user_id)
    
    for user_id in expired_users:
        del user_data[user_id]
    
    if expired_users:
        logger.info(f"Limpiados {len(expired_users)} usuarios expirados")

def validate_config():
    """Validar configuración antes de iniciar"""
    if BOT_TOKEN == "TU_BOT_TOKEN_AQUI":
        print("❌ ERROR: Debes configurar BOT_TOKEN")
        print("💡 Obtén tu token en: https://t.me/BotFather")
        return False
    
    if API_KEY == "TU_API_KEY_AQUI":
        print("❌ ERROR: Debes configurar API_KEY")
        print("💡 Obtén tu API key en: https://alpha.imeicheck.com")
        return False
    
    print("✅ Configuración validada correctamente")
    return True

def run_bot():
    """Función principal para ejecutar el bot"""
    print("🤖 Device Checker Bot - Versión con Autorización y JSON")
    print("=" * 60)
    print("🚀 Iniciando sistema...")
    print("📡 Conectando con Telegram API...")
    print("🔗 Verificando conexión con imeicheck.com...")
    print("🗃️  Inicializando archivos JSON...")
    print("✅ Sistema listo y operativo!")
    print("=" * 60)
    
    # Mostrar información de usuarios autorizados
    auth_users = get_authorized_users()
    print(f"👥 Usuarios autorizados: {len(auth_users)}")
    print(f"📊 Total de servicios disponibles: {sum(len(cat['services']) for cat in SERVICES.values())}")
    print(f"🏷️  Categorías activas: {len(SERVICES)}")
    print("=" * 60)
    
    # Mostrar resumen de usuarios por rol
    role_count = {}
    for user_info in auth_users.values():
        role = user_info.get('role', 'user')
        role_count[role] = role_count.get(role, 0) + 1
    
    for role, count in role_count.items():
        print(f"🔑 {role.title()}: {count} usuario(s)")
    
    print("=" * 60)
    print("🎯 Bot funcionando 24/7...")
    print("💡 Para detener: Ctrl+C")
    print("📋 Comandos admin: /admin para ver panel completo")
    print("=" * 60)
    
    try:
        bot.polling(
            none_stop=True,
            interval=1,
            timeout=60,
            allowed_updates=["message", "callback_query"],
            long_polling_timeout=60
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario")
        print("💾 Guardando datos finales...")
        save_json_data(DATA_FILES["stats"], user_stats)
        print("👋 ¡Hasta luego!")
        
    except Exception as e:
        logger.error(f"Error crítico en el bot: {e}")
        print(f"❌ Error crítico: {e}")
        print("🔄 Reiniciando automáticamente en 10 segundos...")
        time.sleep(10)
        run_bot()

# =================== PUNTO DE ENTRADA PRINCIPAL ===================

if __name__ == "__main__":
    # Configurar logging
    setup_logging()
    
    # Validar configuración
    if not validate_config():
        exit(1)
    
    # Inicializar archivos de datos JSON
    init_data_files()
    
    # Limpiar datos antiguos al iniciar
    cleanup_user_data()
    
    # Mostrar información de inicio
    logger.info("Iniciando Device Checker Bot con sistema de autorización...")
    logger.info(f"Servicios disponibles: {sum(len(cat['services']) for cat in SERVICES.values())}")
    logger.info(f"Categorías: {len(SERVICES)}")
    logger.info(f"Usuarios autorizados: {len(get_authorized_users())}")
    
    # Ejecutar bot
    run_bot()