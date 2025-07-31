from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta


# Добавление навигационных кнопок к существующему построителю клавиатуры
def add_navigation_buttons(builder, prev_state=None):
    builder.button(text="Отменить оформление", callback_data="cancel_order_process")
    return builder


# Клавиатура только с кнопкой отмены
def get_cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Отменить оформление", callback_data="cancel_order_process")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура с кнопками назад и отмены
def get_back_cancel_kb(prev_state):
    builder = InlineKeyboardBuilder()
    builder.button(text="Отменить оформление", callback_data="cancel_order_process")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура для ввода с номером телефона с возможностью пропуска
def get_skip_phone_number_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="skip_phone_number")
    builder = add_navigation_buttons(builder, "name")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура для выбора даты доставки
def get_delivery_date_kb():
    builder = InlineKeyboardBuilder()

    today = datetime.now()

    # Словарь для перевода названий дней недели на русский
    weekdays_ru = {
        'Mon': 'Пн',
        'Tue': 'Вт',
        'Wed': 'Ср',
        'Thu': 'Чт',
        'Fri': 'Пт',
        'Sat': 'Сб',
        'Sun': 'Вс'
    }

    # Словарь для перевода названий месяцев на русский
    months_ru = {
        'Jan': 'янв',
        'Feb': 'фев',
        'Mar': 'мар',
        'Apr': 'апр',
        'May': 'май',
        'Jun': 'июн',
        'Jul': 'июл',
        'Aug': 'авг',
        'Sep': 'сен',
        'Oct': 'окт',
        'Nov': 'ноя',
        'Dec': 'дек'
    }

    for i in range(0, 16):
        date = today + timedelta(days=i)
        date_str = date.strftime("%d.%m.%Y")

        # Получаем название дня недели и месяца на английском
        weekday_en = date.strftime("%a")
        month_en = date.strftime("%b")

        # Заменяем на русский эквивалент
        weekday_ru = weekdays_ru.get(weekday_en, weekday_en)
        month_ru = months_ru.get(month_en, month_en)

        # Специальное название для сегодняшнего дня
        if i == 0:
            date_text = f"{date.strftime('%d')} {month_ru} (Сегодня)"
        else:
            date_text = f"{date.strftime('%d')} {month_ru} ({weekday_ru})"

        builder.button(text=date_text, callback_data=f"date_{date_str}")

    builder = add_navigation_buttons(builder, "phone")
    builder.adjust(2)
    return builder.as_markup()


# Клавиатура для выбора времени доставки
def get_delivery_time_kb():
    builder = InlineKeyboardBuilder()

    # Временные слоты доставки
    time_slots = [
        "Утро",
        "День",
        "Вечер",
        "Ночь",
        "Не имеет значения",
        "Ближайшее свободное время"
    ]

    for slot in time_slots:
        builder.button(text=slot, callback_data=f"time_{slot}")

    builder = add_navigation_buttons(builder, "delivery_date")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура для выбора способа оплаты
def get_payment_method_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Оплата переводом", callback_data="payment_transfer")
    builder.button(text="Оплата наличными", callback_data="payment_cash")
    builder = add_navigation_buttons(builder, "payment")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура для комментария с возможностью пропуска
def get_skip_comment_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="skip_comment")
    builder = add_navigation_buttons(builder, "payment_method")
    builder.adjust(1)
    return builder.as_markup()


# Клавиатура для подтверждения заказа
def get_order_confirmation_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить заказ", callback_data="confirm_order")
    builder.button(text="✏️ Изменить данные", callback_data="edit_order")
    builder.button(text="❌ Отменить заказ", callback_data="cancel_order")
    builder.adjust(1)
    return builder.as_markup()


def get_delivery_address_kb(user_id):
    """
    Клавиатура для выбора адреса доставки с историей адресов
    """
    from database.users.database import get_user_past_addresses

    builder = InlineKeyboardBuilder()

    # Получаем прошлые адреса пользователя
    past_addresses = get_user_past_addresses(user_id)

    if past_addresses:
        # Добавляем заголовок
        builder.button(text="📍 Выберите из прошлых адресов:", callback_data="header_ignore")
        builder.adjust(1)

        # Добавляем прошлые адреса
        for i, address in enumerate(past_addresses):
            # Обрезаем длинные адреса для отображения на кнопке
            display_address = address[:50] + "..." if len(address) > 50 else address
            builder.button(text=display_address, callback_data=f"past_address_{i}")

        # Добавляем кнопку для ввода нового адреса
        builder.button(text="✏️ Ввести новый адрес", callback_data="new_address")

    # Добавляем навигационные кнопки
    builder.button(text="Отменить оформление", callback_data="cancel_order_process")

    # Настраиваем расположение кнопок
    if past_addresses:
        # Заголовок на отдельной строке, адреса по одному, навигация внизу
        adjust_pattern = [1] + [1] * (len(past_addresses) + 1) + [1]
        builder.adjust(*adjust_pattern)
    else:
        builder.adjust(1)

    return builder.as_markup()


def get_promo_code_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="skip_promo_code")
    builder.button(text="❌ Отменить заказ", callback_data="cancel_order_process")
    builder.adjust(1)
    return builder.as_markup()


# Обновленная клавиатура для редактирования заказа
def get_edit_order_kb(delivery_type):
    builder = InlineKeyboardBuilder()
    builder.button(text="Имя", callback_data="edit_name")
    builder.button(text="Телефон", callback_data="edit_phone")
    builder.button(text="Дату доставки", callback_data="edit_delivery_date")
    builder.button(text="Время доставки", callback_data="edit_delivery_time")

    # Если доставка курьером, добавляем опцию изменения адреса
    if delivery_type != "Самовывоз":
        builder.button(text="Адрес доставки", callback_data="edit_address")

    builder.button(text="Способ оплаты", callback_data="edit_payment")
    builder.button(text="Комментарий", callback_data="edit_comment")
    builder.button(text="Промокод", callback_data="edit_promo_code")  # Новая кнопка
    builder.button(text="Вернуться к подтверждению", callback_data="back_to_confirmation")
    builder.button(text="❌ Отменить заказ", callback_data="cancel_order")
    builder.adjust(1)
    return builder.as_markup()
