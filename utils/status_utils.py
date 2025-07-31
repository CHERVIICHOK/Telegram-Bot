# Константы для статусов заказов
ORDER_STATUS = {
    "processing": "Принят на обработку",
    "confirmed": "Подтвержден",
    "assembly": "В сборке",
    "courier": "Передан курьеру",
    "shipped": "Отправлен",
    "delivered": "Доставлен"
}

# Категории статусов заказов для удобной группировки
STATUS_CATEGORIES = {
    "new": {
        "name": "Новые заказы",
        "statuses": ["processing", "confirmed"],
        "emoji": "🆕"
    },
    "in_progress": {
        "name": "В обработке",
        "statuses": ["assembly", "courier", "shipped"],
        "emoji": "🔄"
    },
    "completed": {
        "name": "Завершенные",
        "statuses": ["delivered"],
        "emoji": "✅"
    },
    "all": {
        "name": "Все заказы",
        "statuses": list(ORDER_STATUS.keys()),
        "emoji": "📋"
    }
}


def get_status_key(status_value):
    """Получает ключ статуса по его значению"""
    for key, value in ORDER_STATUS.items():
        if value == status_value:
            return key
    return None


def format_order_info(order):
    """Форматирует информацию о заказе для отображения"""
    status_text = ORDER_STATUS.get(order['status'], "Неизвестный статус")

    order_info = (
        f"Заказ #{order['id']}\n"
        f"👤 Имя: {order['name']}\n"
        f"📞 Телефон: {order['phone']}\n"
        f"📅 Дата доставки: {order['delivery_date']}\n"
        f"🕒 Время доставки: {order['delivery_time']}\n"
        f"🚚 Тип доставки: {order['delivery_type']}\n"
        f"📍 Адрес доставки: {order['delivery_address']}\n"
        f"💳 Способ оплаты: {order['payment_method']}\n"
        f"💬 Комментарий: {order['comment'] or 'Нет'}\n"
        f"⚙️ Статус: {status_text}\n"
        f"🗓️ Создан: {order['created_at']}"
    )
    return order_info


def format_detailed_order_info(order):
    """  
    Форматирует полную информацию о заказе для отображения.  
    Args: order: Словарь с информацией о заказе
    Returns: Строка с подробной информацией о заказе    """
    status_text = ORDER_STATUS.get(order['status'], "Неизвестный статус")

    # Добавляем эмодзи для статуса
    if order['status'] == "processing":
        status_emoji = "⏳"
    elif order['status'] == "confirmed":
        status_emoji = "🗳️"
    elif order['status'] == "assembly":
        status_emoji = "📦"
    elif order['status'] == "courier":
        status_emoji = "📫"
    elif order['status'] == "shipped":
        status_emoji = "🚚"
    elif order['status'] == "delivered":
        status_emoji = "✅"
    elif order['status'] == "canceled":
        status_emoji = "❌"
    else:
        status_emoji = "🐦‍🔥"

    order_info = [
        f"📋 <b>Информация о заказе #{order['id']}</b>",
        f"🕒 <b>Дата заказа:</b> {order['date']}",
        f"⚙️ <b>Статус:</b> {status_emoji} {status_text}",
    ]

    # Информация о клиенте
    if 'customer' in order and order['customer']:
        customer = order['customer']
        order_info.append("\n👤 <b>Информация о клиенте:</b>")

        if 'name' in customer:
            order_info.append(f"• Имя: {customer['name']}")

        if 'phone' in customer:
            order_info.append(f"• Телефон: {customer['phone']}")

        if 'email' in customer:
            order_info.append(f"• Email: {customer['email']}")

            # Адрес доставки
    if 'delivery_address' in order and order['delivery_address']:
        order_info.append("\n🏠 <b>Адрес доставки:</b>")
        order_info.append(f"{order['delivery_address']}")

        # Товары в заказе
    if 'items' in order and order['items']:
        order_info.append("\n🛒 <b>Состав заказа:</b>")

        total_amount = 0
        for item in order['items']:
            item_price = item.get('price', 0)
            item_quantity = item.get('quantity', 1)
            item_total = item_price * item_quantity
            total_amount += item_total

            order_info.append(
                f"• {item.get('name', 'Товар')} - "                f"{item_quantity} шт. x {item_price} = {item_total} руб.")

            # Общая сумма заказа
        order_info.append(f"\n💰 <b>Общая сумма:</b> {total_amount} руб.")

        # Способ оплаты
    if 'payment_method' in order:
        order_info.append(f"💳 <b>Способ оплаты:</b> {order['payment_method']}")

        # Комментарий к заказу
    if 'comment' in order and order['comment']:
        order_info.append(f"\n💬 <b>Комментарий к заказу:</b>\n{order['comment']}")

    return "\n".join(order_info)


def get_status_emoji(status_key):
    """Возвращает эмодзи для статуса заказа"""
    emojis = {
        "processing": "⏳",
        "confirmed": "🗳️",
        "assembly": "📦",
        "courier": "📫",
        "shipped": "🚚",
        "delivered": "✅",
        "canceled": "❌"
    }
    return emojis.get(status_key, "🐦‍🔥")
