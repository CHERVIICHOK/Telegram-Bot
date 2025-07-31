from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar
from aiogram.filters.callback_data import CallbackData
import datetime


class PromoAdminCallback(CallbackData, prefix="promo_admin"):
    action: str
    promo_id: int


class DiscountTypeCallback(CallbackData, prefix="d_type"):
    type_name: str


class PromoEditCallback(CallbackData, prefix="promo_edit"):
    field: str  # 'code', 'description', 'value', 'min_amount', 'end_date', 'max_uses'


class ActionAdminCallback(CallbackData, prefix="action_admin"):
    action: str
    action_id: int


class ActionFSMCallback(CallbackData, prefix="action_fsm"):
    step: str


class ActionEditCallback(CallbackData, prefix="action_edit"):
    field: str


class ActionTargetCallback(CallbackData, prefix="action_target"):
    target_type: str


class ActionCatalogCallback(CallbackData, prefix="action_cat"):
    level: str
    item_index: str


class ActionPaginatorCallback(CallbackData, prefix="action_pag"):
    level: str
    page: int


def get_admin_discounts_menu() -> InlineKeyboardMarkup:
    """Главное меню управления скидками для админа."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎟️ Управление промокодами", callback_data="admin_manage_promos")
    builder.button(text="🔥 Управление акциями", callback_data="admin_manage_actions")
    builder.button(text="⬅️ Назад в админ-панель", callback_data="back_to_admin_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_promo_management_menu() -> InlineKeyboardMarkup:
    """Меню управления промокодами."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать промокод", callback_data="promo_create_start")
    builder.button(text="📋 Список промокодов", callback_data="promo_list_all")
    builder.button(text="⬅️ Назад", callback_data="admin_discounts_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_all_promos_keyboard(promos: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком всех промокодов для управления."""
    builder = InlineKeyboardBuilder()
    if not promos:
        builder.row(InlineKeyboardButton(text="Промокоды не найдены", callback_data="no_op"))

    for promo in promos:
        promo_id, code, is_active, current, total, end_date = promo

        status_icon = "✅" if is_active else "❌"
        try:
            if datetime.datetime.strptime(end_date, '%Y-%m-%d').date() < datetime.date.today():
                status_icon = "🚫"
        except (ValueError, TypeError):
            pass

        # НОВОЕ: Кнопка ведет на детальный просмотр
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} {code} ({current}/{total})",
                callback_data=PromoAdminCallback(action="view", promo_id=promo_id).pack()
            )
        )

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_manage_promos"))
    return builder.as_markup()


def get_promo_admin_view_keyboard(promo_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = "Деактивировать" if is_active else "Активировать"
    builder.button(text=toggle_text, callback_data=PromoAdminCallback(action="toggle", promo_id=promo_id).pack())
    builder.button(text="🗑️ Удалить", callback_data=PromoAdminCallback(action="delete", promo_id=promo_id).pack())
    builder.button(text="⬅️ К списку промокодов", callback_data="promo_list_all")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_promo_delete_confirmation_keyboard(promo_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить",
                   callback_data=PromoAdminCallback(action="confirm_delete", promo_id=promo_id).pack())
    builder.button(text="❌ Нет, отмена", callback_data="promo_list_all")
    return builder.as_markup()


def get_discount_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа скидки с использованием CallbackData."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Процент (%)", callback_data=DiscountTypeCallback(type_name="percentage").pack())
    builder.button(text="Фиксированная сумма (₽)", callback_data=DiscountTypeCallback(type_name="fixed_amount").pack())
    return builder.as_markup()


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_action")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    return builder.as_markup()


def get_skip_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Пропустить'."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Пропустить", callback_data="skip_step")
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Отмена' для FSM."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить создание", callback_data="fsm_cancel")
    return builder.as_markup()


def get_deal_management_menu() -> InlineKeyboardMarkup:
    """Меню управления 'Товаром дня'."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать/Изменить на дату", callback_data="deal_create_start")
    builder.button(text="🗑️ Удалить на дату", callback_data="deal_delete_start")
    builder.button(text="⬅️ Назад", callback_data="admin_discounts_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_promo_code_input_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Сгенерировать", callback_data="promo_generate_code")
    builder.button(text="❌ Отменить создание", callback_data="fsm_cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_promo_generation_choice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Оставить этот", callback_data="promo_accept_generated")
    builder.button(text="🔄 Сгенерировать другой", callback_data="promo_regenerate")
    builder.button(text="⌨️ Ввести вручную", callback_data="promo_enter_manual")
    builder.button(text="❌ Отменить создание", callback_data="fsm_cancel")
    builder.adjust(1, 2, 1)
    return builder.as_markup()


def get_promo_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить и создать", callback_data="confirm_action")
    builder.row(
        InlineKeyboardButton(text="✏️ Код", callback_data=PromoEditCallback(field="code").pack()),
        InlineKeyboardButton(text="✏️ Описание", callback_data=PromoEditCallback(field="description").pack())
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Скидка", callback_data=PromoEditCallback(field="value").pack()),
        InlineKeyboardButton(text="✏️ Мин. заказ", callback_data=PromoEditCallback(field="min_amount").pack())
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Дата", callback_data=PromoEditCallback(field="end_date").pack()),
        InlineKeyboardButton(text="✏️ Лимит использований", callback_data=PromoEditCallback(field="max_uses").pack())
    )
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1, 2, 2, 2)
    return builder.as_markup()


async def get_calendar(min_date: datetime.date | None = None) -> InlineKeyboardMarkup:
    """
    Создает inline-календарь.
    :param min_date: Минимально допустимая для выбора дата.
    """
    calendar = SimpleCalendar(show_alerts=True)

    # Устанавливаем диапазон дат. Если min_date задана, даты до нее будут неактивны.
    start_range = min_date if min_date else datetime.date.today()

    calendar.set_dates_range(
        datetime.datetime.combine(start_range, datetime.time.min),
        datetime.datetime(2030, 1, 1)
    )

    return await calendar.start_calendar()


def get_action_management_menu() -> InlineKeyboardMarkup:
    """Меню управления акциями."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать акцию", callback_data="action_create_start")
    builder.button(text="📋 Список всех акций", callback_data="action_list_all")
    builder.button(text="⬅️ Назад", callback_data="admin_discounts_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_all_actions_keyboard(actions: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком всех акций для управления."""
    builder = InlineKeyboardBuilder()
    today = datetime.date.today()
    for action in actions:
        action_id, title, start_date_str, end_date_str, is_active = action
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if not is_active:
            status_icon = "❌"  # Деактивирована
        elif end_date < today:
            status_icon = "🚫"  # Прошедшая
        elif start_date > today:
            status_icon = "⏳"  # Будущая
        else:
            status_icon = "✅"  # Активная

        builder.button(
            text=f"{status_icon} {title}",
            callback_data=ActionAdminCallback(action="view", action_id=action_id).pack()
        )

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_manage_actions"))
    builder.adjust(1)
    return builder.as_markup()


def get_action_admin_view_keyboard(action_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = "Деактивировать" if is_active else "Активировать"
    builder.button(text=toggle_text, callback_data=ActionAdminCallback(action="toggle", action_id=action_id).pack())
    builder.button(text="🗑️ Удалить", callback_data=ActionAdminCallback(action="delete", action_id=action_id).pack())
    builder.button(text="⬅️ К списку акций", callback_data="action_list_all")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_action_delete_confirmation_keyboard(action_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить",
                   callback_data=ActionAdminCallback(action="confirm_delete", action_id=action_id).pack())
    builder.button(text="❌ Нет, отмена", callback_data="action_list_all")
    return builder.as_markup()


def get_action_fsm_nav_keyboard(back_step: str | None = None) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для FSM с кнопками 'Назад' и 'Отмена'."""
    builder = InlineKeyboardBuilder()
    if back_step:
        builder.button(text="⬅️ Назад", callback_data=ActionFSMCallback(step=back_step).pack())
    builder.button(text="❌ Отменить создание", callback_data="fsm_cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_action_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для шага подтверждения создания акции."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить и создать", callback_data="action_confirm_creation")
    builder.row(
        InlineKeyboardButton(text="✏️ Название", callback_data=ActionEditCallback(field="title").pack()),
        InlineKeyboardButton(text="✏️ Описание", callback_data=ActionEditCallback(field="description").pack())
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Скидка", callback_data=ActionEditCallback(field="discount_value").pack())
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Дата начала", callback_data=ActionEditCallback(field="start_date").pack()),
        InlineKeyboardButton(text="✏️ Дата конца", callback_data=ActionEditCallback(field="end_date").pack())
    )
    builder.button(text="❌ Отмена", callback_data="fsm_cancel")
    builder.adjust(1, 2, 1, 2, 1)
    return builder.as_markup()


def get_action_target_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа цели акции."""
    builder = InlineKeyboardBuilder()
    builder.button(text="На всю Категорию", callback_data=ActionTargetCallback(target_type="category").pack())
    builder.button(text="На линейку Товаров", callback_data=ActionTargetCallback(target_type="product_name").pack())
    builder.button(text="На конкретный Товар (вкус)",
                   callback_data=ActionTargetCallback(target_type="product_full_name").pack())
    builder.button(text="❌ Отменить создание", callback_data="fsm_cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_catalog_keyboard(level: str, items: list, page: int = 0) -> InlineKeyboardMarkup:
    """
    Динамическая клавиатура для навигации по каталогу с пагинацией.
    """
    builder = InlineKeyboardBuilder()
    PAGE_SIZE = 8  # Кнопок на одной странице

    start_index = page * PAGE_SIZE
    end_index = start_index + PAGE_SIZE

    # Срез элементов для текущей страницы
    paginated_items = items[start_index:end_index]

    for index, item in enumerate(paginated_items):
        # Реальный индекс в полном списке
        original_index = start_index + index

        if level == 'flavor':  # Для вкусов item это кортеж (id, name)
            text = item[1]
        else:  # Для категорий и названий item это строка
            text = item

        builder.button(
            text=text,
            callback_data=ActionCatalogCallback(level=level, item_index=str(original_index)).pack()
        )

    # Создание кнопок пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=ActionPaginatorCallback(level=level, page=page - 1).pack()
        ))
    if end_index < len(items):
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=ActionPaginatorCallback(level=level, page=page + 1).pack()
        ))

    # Добавляем кнопки в строку
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="❌ Отменить создание", callback_data="fsm_cancel"))
    builder.adjust(1)  # Все кнопки товаров в один столбец
    return builder.as_markup()
