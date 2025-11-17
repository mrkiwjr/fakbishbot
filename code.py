import os
import asyncio
import json
import logging
import shutil
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_ID = int(os.environ['ADMIN_ID'])

# ==================== ВЕБ-ПАНЕЛЬ ====================
web_app = Flask(__name__)


@web_app.route('/')
def admin_panel():
    """Веб-панель управления ботом"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Панель управления ботом</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            .stats { background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .user-list { max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; }
            .user-item { padding: 8px; border-bottom: 1px solid #eee; }
            .actions { margin-top: 20px; }
            button { background: #2196F3; color: white; border: none; padding: 10px 15px; margin: 5px; border-radius: 5px; cursor: pointer; }
            button:hover { background: #1976D2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Панель управления ботом</h1>

            <div class="stats">
                <h3>Статистика</h3>
                <p><strong>Всего подписчиков:</strong> {{ count }}</p>
                <p><strong>Новых за неделю:</strong> {{ weekly_count }}</p>
                <p><strong>Последнее обновление:</strong> {{ last_update }}</p>
            </div>

            <div class="actions">
                <button onclick="location.href='/backup'">Создать бэкап</button>
                <button onclick="location.href='/logs'">Показать логи</button>
                <button onclick="location.href='/stats'">Детальная статистика</button>
            </div>

            <h3>Список подписчиков</h3>
            <div class="user-list">
                {% for user in users %}
                <div class="user-item">
                    <strong>{{ user.name }}</strong> 
                    (ID: {{ user.id }}) 
                    {% if user.username and user.username != 'нет' %}@{{ user.username }}{% endif %}
                    <br><small>Подписался: {{ user.joined_at }}</small>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """

    # Статистика за неделю
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    weekly_count = len(
        [u for u in subscribers if u.get('joined_at', '') >= week_ago])

    return render_template_string(
        html,
        count=len(subscribers),
        weekly_count=weekly_count,
        last_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        users=reversed(subscribers[-50:]))


@web_app.route('/backup')
def create_backup_web():
    """Создать бэкап через веб"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup/subscribers_backup_{timestamp}.json"
        os.makedirs('backup', exist_ok=True)
        shutil.copy2('subscribers.json', backup_filename)
        return f"Бэкап создан: {backup_filename}"
    except Exception as e:
        return f"Ошибка: {e}"


@web_app.route('/logs')
def show_logs():
    """Показать логи через веб"""
    try:
        with open('bot_log.txt', 'r', encoding='utf-8') as f:
            logs = f.read()
        return f"<pre>{logs}</pre>"
    except:
        return "Логи не найдены"


@web_app.route('/stats')
def web_stats():
    """Детальная статистика через веб"""
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    recent_users = [u for u in subscribers if 'joined_at' in u]
    weekly_users = len([
        u for u in recent_users
        if u.get('joined_at', '') >= week_ago.strftime("%Y-%m-%d")
    ])
    monthly_users = len([
        u for u in recent_users
        if u.get('joined_at', '') >= month_ago.strftime("%Y-%m-%d")
    ])

    stats_html = f"""
    <h2>Детальная статистика</h2>
    <div style="background: #e8f5e8; padding: 15px; border-radius: 5px;">
        <p><strong>Всего подписчиков:</strong> {len(subscribers)}</p>
        <p><strong>Новых за неделю:</strong> {weekly_users}</p>
        <p><strong>Новых за месяц:</strong> {monthly_users}</p>
        <p><strong>Дата запуска:</strong> {get_bot_start_time()}</p>
    </div>
    <br>
    <a href="/">Назад</a>
    """
    return stats_html


def run_web_server():
    """Запуск веб-сервера"""
    web_app.run(host='0.0.0.0', port=8080, debug=False)


# ==================== СИСТЕМА ЛОГИРОВАНИЯ ====================
def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.FileHandler('bot_log.txt',
                                                encoding='utf-8'),
                            logging.StreamHandler()
                        ])


def log_action(action, user_id=None, details="", level="INFO"):
    """Логирование действий"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {action}"

    if user_id:
        log_message += f" | User: {user_id}"
    if details:
        log_message += f" | Details: {details}"

    # Записываем в файл
    with open('bot_log.txt', 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')

    # Выводим в консоль
    print(log_message)


# ==================== СИСТЕМА ХРАНЕНИЯ ====================
subscribers = []
last_broadcast_time = None
bot_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_bot_start_time():
    return bot_start_time


def save_subscribers():
    """Сохранить подписчиков в файл"""
    try:
        with open('subscribers.json', 'w', encoding='utf-8') as f:
            json.dump(subscribers, f, ensure_ascii=False, indent=2)
        log_action("DATA_SAVED", details=f"Subscribers: {len(subscribers)}")
    except Exception as e:
        log_action("SAVE_ERROR", details=str(e), level="ERROR")


def load_subscribers():
    """Загрузить подписчиков из файла"""
    try:
        if os.path.exists('subscribers.json'):
            with open('subscribers.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                log_action("DATA_LOADED",
                           details=f"Loaded {len(data)} subscribers")
                return data
    except Exception as e:
        log_action("LOAD_ERROR", details=str(e), level="ERROR")
    return []


# ==================== ШАБЛОНЫ СООБЩЕНИЙ ====================
MESSAGE_TEMPLATES = {
    'promo': "Промокод ночь {code}",
    'welcome': """Добро пожаловать, {name}!

Вы подписались на рассылку промокодов от канала @testtestpromik

Теперь вы будете получать:
- Эксклюзивные промокоды
- Специальные предложения
- Уведомления о акциях

Отписаться: напишите /stop""",
    'news': "{message}",
    'goodbye': "Вы отписаны от рассылки. Будем ждать вас снова!",
    'activity_check': "Проверка активности..."
}


# ==================== ФУНКЦИИ БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда start - подписка на рассылку"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Пользователь"

    if not any(user['id'] == user_id for user in subscribers):
        subscribers.append({
            'id':
            user_id,
            'name':
            user_name,
            'username':
            update.effective_user.username or "нет",
            'joined_at':
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_subscribers()

        # Отправляем приветствие
        welcome_text = MESSAGE_TEMPLATES['welcome'].format(name=user_name)
        await update.message.reply_text(welcome_text)

        # Уведомляем администратора
        await notify_admin(context,
                           f"Новый подписчик: {user_name} (ID: {user_id})")
        log_action("USER_JOINED", user_id=user_id, details=user_name)
    else:
        await update.message.reply_text("Вы уже в списке рассылки!")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда stop - отписка от рассылки"""
    user_id = update.effective_user.id

    user_to_remove = None
    for user in subscribers:
        if user['id'] == user_id:
            user_to_remove = user
            break

    if user_to_remove:
        subscribers.remove(user_to_remove)
        save_subscribers()
        await update.message.reply_text(MESSAGE_TEMPLATES['goodbye'])
        log_action("USER_LEFT",
                   user_id=user_id,
                   details=user_to_remove['name'])
    else:
        await update.message.reply_text("Вы не были подписаны на рассылку.")


async def send_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассылка промокода"""
    global last_broadcast_time

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Только для администратора")
        return

    # Проверка частоты рассылок
    if last_broadcast_time and datetime.now(
    ) - last_broadcast_time < timedelta(minutes=2):
        await update.message.reply_text(
            "Слишком частая рассылка! Подождите 2 минуты.")
        return

    if not context.args:
        await update.message.reply_text("Использование: /send_promo КОД")
        return

    if len(subscribers) == 0:
        await update.message.reply_text("Список подписчиков пуст!")
        return

    promo_code = " ".join(context.args)
    message_text = MESSAGE_TEMPLATES['promo'].format(code=promo_code)

    sent = 0
    failed = 0
    failed_users = []

    await update.message.reply_text(
        f"Рассылка для {len(subscribers)} подписчиков...")

    for user in subscribers:
        try:
            await context.bot.send_message(user['id'], message_text)
            sent += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            failed += 1
            failed_users.append(user['id'])
            log_action("SEND_ERROR",
                       user_id=user['id'],
                       details=str(e),
                       level="ERROR")

    last_broadcast_time = datetime.now()

    # Отчет
    report = f"Рассылка завершена! Отправлено: {sent}, Ошибок: {failed}"
    if failed_users:
        report += f"\n\nНедоступные пользователи: {', '.join(map(str, failed_users[:5]))}"

    await update.message.reply_text(report)
    log_action("PROMO_SENT",
               details=f"Code: {promo_code}, Sent: {sent}, Failed: {failed}")


async def send_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка кастомного сообщения"""
    global last_broadcast_time

    if update.effective_user.id != ADMIN_ID:
        return

    if last_broadcast_time and datetime.now(
    ) - last_broadcast_time < timedelta(minutes=2):
        await update.message.reply_text(
            "Слишком частая рассылка! Подождите 2 минуты.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Использование: /send_custom ТЕКСТ")
        return

    message_text = " ".join(context.args)

    sent = 0
    failed = 0

    await update.message.reply_text(
        f"Отправка кастомного сообщения для {len(subscribers)} подписчиков...")

    for user in subscribers:
        try:
            await context.bot.send_message(user['id'], message_text)
            sent += 1
            await asyncio.sleep(0.3)
        except:
            failed += 1

    last_broadcast_time = datetime.now()
    await update.message.reply_text(
        f"Кастомное сообщение отправлено {sent} пользователям")
    log_action("CUSTOM_MESSAGE_SENT",
               details=f"Message: {message_text[:50]}..., Sent: {sent}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика подписчиков"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Только для администратора")
        return

    stats_text = f"Подписчиков: {len(subscribers)}\n\n"
    for user in subscribers[-10:]:
        join_date = user.get('joined_at', 'неизвестно')
        stats_text += f"- {user['name']} (ID: {user['id']}) - {join_date}\n"

    await update.message.reply_text(stats_text)


async def detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подробная статистика"""
    if update.effective_user.id != ADMIN_ID:
        return

    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    recent_users = [u for u in subscribers if 'joined_at' in u]
    weekly_users = len([
        u for u in recent_users
        if u.get('joined_at', '') >= week_ago.strftime("%Y-%m-%d")
    ])
    monthly_users = len([
        u for u in recent_users
        if u.get('joined_at', '') >= month_ago.strftime("%Y-%m-%d")
    ])

    stats_text = f"""
Детальная статистика:

Всего подписчиков: {len(subscribers)}
Новых за неделю: {weekly_users}
Новых за месяц: {monthly_users}
Дата запуска бота: {bot_start_time}

Последние 5 подписчиков:
"""

    for user in recent_users[-5:]:
        stats_text += f"- {user['name']} (@{user['username']}) - {user.get('joined_at', 'неизвестно')}\n"

    await update.message.reply_text(stats_text)


async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать резервную копию"""
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup/subscribers_backup_{timestamp}.json"
        os.makedirs('backup', exist_ok=True)
        shutil.copy2('subscribers.json', backup_filename)
        await update.message.reply_text(f"Бэкап создан: {backup_filename}")
        log_action("BACKUP_CREATED", details=backup_filename)
    except Exception as e:
        await update.message.reply_text(f"Ошибка создания бэкапа: {e}")
        log_action("BACKUP_ERROR", details=str(e), level="ERROR")


async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить пользователя из рассылки"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Только для администратора")
        return

    if not context.args:
        if not subscribers:
            await update.message.reply_text("Список подписчиков пуст!")
            return

        users_text = "Укажите ID пользователя для удаления:\n\n"
        for i, user in enumerate(subscribers, 1):
            users_text += f"{i}. {user['name']} (ID: {user['id']})\n"

        users_text += "\nДля удаления используйте: /remove ID\nПример: /remove 123456789"
        await update.message.reply_text(users_text)
        return

    try:
        user_id_to_remove = int(context.args[0])

        user_to_remove = None
        for user in subscribers:
            if user['id'] == user_id_to_remove:
                user_to_remove = user
                break

        if user_to_remove:
            subscribers.remove(user_to_remove)
            save_subscribers()
            await update.message.reply_text(
                f"Пользователь удален!\n"
                f"Имя: {user_to_remove['name']}\n"
                f"ID: {user_to_remove['id']}\n"
                f"Осталось подписчиков: {len(subscribers)}")
            log_action("USER_REMOVED_BY_ADMIN",
                       user_id=user_id_to_remove,
                       details=user_to_remove['name'])
        else:
            await update.message.reply_text(
                f"Пользователь с ID {user_id_to_remove} не найден")

    except ValueError:
        await update.message.reply_text(
            "Неверный формат ID. Используйте: /remove ID")


async def check_active_users(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    """Проверить активных пользователей"""
    if update.effective_user.id != ADMIN_ID:
        return

    active_count = 0
    inactive_count = 0
    inactive_users = []

    await update.message.reply_text("Проверяю активность пользователей...")

    for user in subscribers:
        try:
            await context.bot.send_message(user['id'],
                                           MESSAGE_TEMPLATES['activity_check'])
            active_count += 1
            await asyncio.sleep(0.1)
        except:
            inactive_count += 1
            inactive_users.append(user['id'])

    result = f"Результаты проверки:\nАктивных: {active_count}\nНеактивных: {inactive_count}"

    if inactive_users:
        result += f"\n\nНеактивные пользователи (первые 10): {', '.join(map(str, inactive_users[:10]))}"
        result += f"\n\nУдалить неактивных: /cleanup_inactive"

    await update.message.reply_text(result)
    log_action("ACTIVITY_CHECK",
               details=f"Active: {active_count}, Inactive: {inactive_count}")


async def cleanup_inactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить неактивных пользователей"""
    if update.effective_user.id != ADMIN_ID:
        return

    removed_count = 0
    await update.message.reply_text(
        "Начинаю очистку неактивных пользователей...")

    for user in subscribers[:]:
        try:
            await context.bot.send_message(user['id'],
                                           MESSAGE_TEMPLATES['activity_check'])
            await asyncio.sleep(0.1)
        except:
            subscribers.remove(user)
            removed_count += 1

    if removed_count > 0:
        save_subscribers()
        await update.message.reply_text(
            f"Удалено {removed_count} неактивных пользователей")
        log_action("INACTIVE_CLEANED", details=f"Removed: {removed_count}")
    else:
        await update.message.reply_text("Неактивных пользователей не найдено")


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Отправить уведомление администратору"""
    try:
        await context.bot.send_message(ADMIN_ID, f"Уведомление: {message}")
    except Exception as e:
        log_action("NOTIFY_ERROR", details=str(e), level="ERROR")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам"""
    help_text = """
Бот для рассылки промокодов

Команды для всех:
/start - добавиться в рассылку
/stop - отписаться от рассылки
/help - справка

Команды для администратора:
/send_promo КОД - рассылка промокода
/send_custom ТЕКСТ - кастомное сообщение
/stats - статистика
/detailed_stats - детальная статистика
/remove ID - удалить пользователя
/backup - создать бэкап
/check_active - проверить активность
/cleanup_inactive - удалить неактивных

Веб-панель: ваш-url.repl.co
"""
    await update.message.reply_text(help_text)


# ==================== ЗАПУСК БОТА ====================
def main():
    # Загружаем данные
    global subscribers
    subscribers = load_subscribers()

    # Настраиваем логирование
    setup_logging()

    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    log_action("WEB_SERVER_STARTED", details="Port 8080")

    # Запускаем Telegram бота
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем команды
    commands = [
        ("start", start),
        ("stop", stop),
        ("send_promo", send_promo),
        ("send_custom", send_custom),
        ("stats", stats),
        ("detailed_stats", detailed_stats),
        ("backup", backup),
        ("remove", remove_user),
        ("check_active", check_active_users),
        ("cleanup_inactive", cleanup_inactive),
        ("help", help_command),
    ]

    for command, handler in commands:
        application.add_handler(CommandHandler(command, handler))

    print("=" * 50)
    print("Бот запущен!")
    print(f"Подписчиков загружено: {len(subscribers)}")
    print(f"Веб-панель: https://ваш-реплит.username.repl.co")
    print(f"Время запуска: {bot_start_time}")
    print("=" * 50)

    log_action("BOT_STARTED", details=f"Subscribers: {len(subscribers)}")

    application.run_polling()


if __name__ == "__main__":
    main()
