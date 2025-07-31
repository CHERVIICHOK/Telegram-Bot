import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import re


def format_broadcast_message(text: str, product_data: Optional[Dict] = None) -> str:
    """Форматирует текст рассылки, подставляя данные о товаре, если указаны."""
    if not product_data:
        return text

    # Заменяем переменные в тексте на данные о товаре
    replacements = {
        "{product_name}": product_data.get("product_name", ""),
        "{product_full_name}": product_data.get("product_full_name", ""),
        "{price}": str(product_data.get("price", "")),
        "{description}": product_data.get("description", ""),
        "{category}": product_data.get("category", "")
    }

    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)

    return text


def parse_button_data(text: str) -> List[Dict[str, str]]:
    """Парсит текст с описанием кнопок в формате 'текст|url'."""
    buttons = []
    lines = text.strip().split('\n')

    for line in lines:
        parts = line.split('|', 1)
        if len(parts) == 2:
            button_text = parts[0].strip()
            button_url = parts[1].strip()

            # Проверяем, что URL валидный
            if button_url.startswith("http://") or button_url.startswith("https://"):
                buttons.append({
                    "text": button_text,
                    "url": button_url
                })

    return buttons


def validate_buttons_format(text: str) -> Tuple[bool, str]:
    """Проверяет правильность формата кнопок."""
    if not text.strip():
        return True, ""

    lines = text.strip().split('\n')

    for i, line in enumerate(lines, 1):
        parts = line.split('|', 1)
        if len(parts) != 2:
            return False, f"Ошибка в строке {i}: неправильный формат. Должно быть 'текст|url'"

        button_text = parts[0].strip()
        button_url = parts[1].strip()

        if not button_text:
            return False, f"Ошибка в строке {i}: текст кнопки не может быть пустым"

        if not (button_url.startswith("http://") or button_url.startswith("https://")):
            return False, f"Ошибка в строке {i}: URL должен начинаться с http:// или https://"

    return True, ""


def format_broadcast_preview(broadcast_data: Dict[str, Any]) -> str:
    """Форматирует превью рассылки для отображения администратору."""
    message_text = broadcast_data.get("text", "")
    target_type = broadcast_data.get("target_type", "all")
    recipients_count = broadcast_data.get("total_recipients", 0)

    target_description = {
        "all": "Все пользователи",
        "active": f"Активные пользователи за последние {broadcast_data.get('active_days', 30)} дней",
        "region": f"Пользователи из региона: {broadcast_data.get('region', 'Не указан')}"
    }.get(target_type, "Неизвестная группа")

    preview = (
        f"📤 <b>Предпросмотр рассылки</b>\n\n"
        f"📝 <b>Текст сообщения:</b>\n"
        f"{message_text}\n\n"
        f"👥 <b>Целевая аудитория:</b> {target_description}\n"
        f"🔢 <b>Количество получателей:</b> {recipients_count}"
    )

    media_type = broadcast_data.get("media_type")
    if media_type:
        media_description = "Фото" if media_type == "photo" else "Файл"
        preview += f"\n📎 <b>Вложение:</b> {media_description}"

    buttons = broadcast_data.get("buttons", [])
    if buttons:
        preview += "\n🔘 <b>Кнопки:</b> Да"

    return preview


def format_broadcast_history_item(broadcast: tuple) -> str:
    """Форматирует запись из истории рассылок для отображения."""
    broadcast_id, message_text, target_type, sent_count, total_recipients, status, created_at, sent_at = broadcast

    if isinstance(created_at, str):
        created_date = created_at
    else:
        created_date = "Неизвестно"

    if isinstance(sent_at, str) and sent_at:
        sent_date = sent_at
    else:
        sent_date = "Не отправлено"

    status_text = {
        "completed": "✅ Завершена",
        "pending": "🕒 В процессе",
        "failed": "❌ Ошибка",
        "canceled": "⛔ Отменена"
    }.get(status, status)

    target_text = {
        "all": "Все пользователи",
        "active": "Активные пользователи",
        "region": "По региону"
    }.get(target_type, target_type)

    # Сокращаем текст сообщения, если он слишком длинный
    if len(message_text) > 100:
        message_preview = message_text[:97] + "..."
    else:
        message_preview = message_text

    return (
        f"📤 <b>Рассылка #{broadcast_id}</b>\n\n"
        f"📝 <b>Текст:</b> {message_preview}\n"
        f"👥 <b>Аудитория:</b> {target_text}\n"
        f"📊 <b>Отправлено:</b> {sent_count}/{total_recipients}\n"
        f"📅 <b>Создана:</b> {created_date}\n"
        f"📅 <b>Отправлена:</b> {sent_date}\n"
        f"📌 <b>Статус:</b> {status_text}"
    )


def format_broadcast_details(broadcast: tuple) -> str:
    """Форматирует детальную информацию о рассылке."""
    (broadcast_id, message_text, media_type, media_file, buttons_json,
     target_type, target_params, sent_count, total_recipients,
     status, created_at, sent_at) = broadcast

    # Конвертируем JSON в объекты Python
    try:
        buttons = json.loads(buttons_json) if buttons_json else []
        target_params = json.loads(target_params) if target_params else {}
    except json.JSONDecodeError:
        buttons = []
        target_params = {}

    # Форматируем значения
    status_text = {
        "completed": "✅ Завершена",
        "pending": "🕒 В процессе",
        "failed": "❌ Ошибка",
        "canceled": "⛔ Отменена"
    }.get(status, status)

    target_text = {
        "all": "Все пользователи",
        "active": f"Активные пользователи за последние {target_params.get('days', 30)} дней",
        "region": f"Пользователи из региона: {target_params.get('region', 'Не указан')}"
    }.get(target_type, target_type)

    if isinstance(created_at, str):
        created_date = created_at
    else:
        created_date = "Неизвестно"

    if isinstance(sent_at, str) and sent_at:
        sent_date = sent_at
    else:
        sent_date = "Не отправлено"

    media_info = ""
    if media_type:
        media_text = "Фото" if media_type == "photo" else "Файл"
        media_info = f"📎 <b>Вложение:</b> {media_text}\n"

    buttons_info = ""
    if buttons:
        buttons_count = len(buttons)
        buttons_info = f"🔘 <b>Кнопки:</b> {buttons_count}\n"

    delivery_rate = (sent_count / total_recipients * 100) if total_recipients > 0 else 0

    return (
        f"📤 <b>Детали рассылки #{broadcast_id}</b>\n\n"
        f"📝 <b>Текст сообщения:</b>\n{message_text}\n\n"
        f"{media_info}"
        f"{buttons_info}"
        f"👥 <b>Целевая аудитория:</b> {target_text}\n"
        f"📊 <b>Статистика доставки:</b> {sent_count}/{total_recipients} ({delivery_rate:.1f}%)\n"
        f"📅 <b>Создана:</b> {created_date}\n"
        f"📅 <b>Отправлена:</b> {sent_date}\n"
        f"📌 <b>Статус:</b> {status_text}"
    )


def parse_scheduled_time(time_string: str) -> Optional[datetime]:
    """Парсит строку со временем в формат datetime."""
    # Поддерживаемые форматы: ДД.ММ.ГГГГ ЧЧ:ММ или ЧЧ:ММ (сегодня)
    time_string = time_string.strip()

    # Формат ЧЧ:ММ (сегодня)
    time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
    match = time_pattern.match(time_string)
    if match:
        hour, minute = map(int, match.groups())
        now = datetime.now()
        scheduled_time = datetime(now.year, now.month, now.day, hour, minute)

        # Если время уже прошло, переносим на завтра
        if scheduled_time < now:
            scheduled_time = scheduled_time.replace(day=now.day + 1)

        return scheduled_time

    # Формат ДД.ММ.ГГГГ ЧЧ:ММ
    date_time_pattern = re.compile(r'^(\d{2})\.(\d{2})\.(\d{4}) ([01]?[0-9]|2[0-3]):([0-5][0-9])$')
    match = date_time_pattern.match(time_string)
    if match:
        day, month, year, hour, minute = map(int, match.groups())
        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            return None

    return None