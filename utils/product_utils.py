from typing import Dict, Any, Optional, Tuple


def format_product_details(product: tuple) -> str:
    """Форматирует информацию о товаре для отображения пользователю."""
    if not product or len(product) < 9:
        return "Информация о товаре не найдена."

    product_id, category, product_name, product_full_name, flavor, price, description, quantity, image_path = product[
                                                                                                              :9]
    is_active = product[9] if len(product) > 9 else 1

    status = "✅ Активен" if is_active else "❌ Деактивирован"

    return (
        f"📦 <b>Товар:</b> {product_full_name}\n"
        f"🔍 <b>ID:</b> {product_id}\n"
        f"🗂 <b>Категория:</b> {category}\n"
        f"📝 <b>Название:</b> {product_name}\n"
        f"🍬 <b>Вкус:</b> {flavor}\n"
        f"💰 <b>Цена:</b> {price} ₽\n"
        f"🔢 <b>Количество на складе:</b> {quantity} шт.\n"
        f"📋 <b>Описание:</b> {description or 'Отсутствует'}\n"
        f"🖼 <b>Путь к изображению:</b> {image_path or 'Отсутствует'}\n"
        f"📊 <b>Статус:</b> {status}"
    )


def validate_product_data(field: str, value: str) -> Tuple[bool, str]:
    """Проверяет валидность данных товара."""
    if field == "category" and not value.strip():
        return False, "Категория не может быть пустой"

    if field == "product_name" and not value.strip():
        return False, "Название товара не может быть пустым"

    if field == "price":
        try:
            price = float(value)
            if price < 0:
                return False, "Цена не может быть отрицательной"
        except ValueError:
            return False, "Цена должна быть числом"

    if field == "quantity":
        try:
            quantity = int(value)
            if quantity < 0:
                return False, "Количество не может быть отрицательным"
        except ValueError:
            return False, "Количество должно быть целым числом"

    return True, "Данные валидны"


def prepare_product_data(field: str, value: str, product_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Подготавливает данные товара для обновления в базе данных."""
    data = product_data or {}

    if field == "price":
        data[field] = float(value)
    elif field == "quantity":
        data[field] = int(value)
    else:
        data[field] = value

    # Если изменяется название товара или Вкус, обновляем полное название
    if field in ["product_name", "flavor"] and ("product_name" in data or "flavor" in data):
        product_name = data.get("product_name", "")
        flavor = data.get("flavor", "")
        if product_name and flavor:
            data["product_full_name"] = f"{product_name} {flavor}"

    return data


def get_field_description(field: str) -> str:
    """Возвращает описание поля товара."""
    descriptions = {
        "category": "категорию",
        "product_name": "название товара",
        "flavor": "Вкус товара",
        "price": "цену товара (в рублях)",
        "description": "описание товара",
        "quantity": "количество товара на складе",
        "image_path": "путь к изображению товара"
    }
    return descriptions.get(field, field)


def get_field_prompt(field: str) -> str:
    """Возвращает подсказку для ввода значения поля."""
    prompts = {
        "category": "Введите категорию товара:",
        "product_name": "Введите название товара:",
        "flavor": "Введите Вкус товара (если есть):",
        "price": "Введите цену товара (в рублях):",
        "description": "Введите описание товара (или отправьте '-' чтобы пропустить):",
        "quantity": "Введите количество товара на складе:",
        "image_path": "Введите путь к изображению товара (или отправьте '-' чтобы пропустить):"
    }
    return prompts.get(field, f"Введите {field}:")