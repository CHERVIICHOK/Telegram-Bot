import sqlite3
import os
import random
from config import  DATABASE_NAME


def create_connection():
    """Создает соединение с базой данных."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
    except sqlite3.Error as e:
        print(f"Ошибка подключения к базе данных {DATABASE_NAME}: {e}")
    return conn


def create_tables(conn):
    """Создает необходимые таблицы в базе данных."""
    try:
        cursor = conn.cursor()

        # Создаем таблицу для товаров
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            product_name TEXT NOT NULL,
            product_full_name TEXT NOT NULL,
            flavor TEXT,
            price REAL NOT NULL,
            description TEXT,
            quantity INTEGER DEFAULT 0,
            image_path TEXT,
            is_active INTEGER DEFAULT 1
        )
        ''')

        conn.commit()
        print("Таблицы успешно созданы.")
    except sqlite3.Error as e:
        print(f"Ошибка при создании таблиц: {e}")


def seed_data(conn):
    """Заполняет базу данных тестовыми данными."""
    try:
        cursor = conn.cursor()

        # Очищаем таблицу перед заполнением
        cursor.execute("DELETE FROM products")

        # Создаем папку для изображений, если её нет
        images_dir = "images"
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
            print(f"Создана директория {images_dir} для хранения изображений.")

        # Тестовые данные для вейпов
        vapes = [
            {
                "category": "Вейпы",
                "product_name": "Одноразовые",
                "product_full_name": "Elf Bar BC5000",
                "flavor": "Клубника",
                "price": 1200,
                "description": "Одноразовая электронная сигарета Elf Bar BC5000 с ёмкостью аккумулятора 650 мАч. До 5000 затяжек.",
                "quantity": random.randint(5, 20),
                "image_path": "images/elfbar_strawberry.jpg"
            },
            {
                "category": "Вейпы",
                "product_name": "Одноразовые",
                "product_full_name": "Elf Bar BC5000",
                "flavor": "Ягодный микс",
                "price": 1200,
                "description": "Одноразовая электронная сигарета Elf Bar BC5000 с ёмкостью аккумулятора 650 мАч. До 5000 затяжек.",
                "quantity": random.randint(5, 20),
                "image_path": "images/elfbar_berry.jpg"
            },
            {
                "category": "Вейпы",
                "product_name": "Одноразовые",
                "product_full_name": "HQD Cuvie Plus",
                "flavor": "Виноград",
                "price": 950,
                "description": "Одноразовая электронная сигарета HQD Cuvie Plus с ёмкостью аккумулятора 550 мАч. До 1200 затяжек.",
                "quantity": random.randint(5, 20),
                "image_path": "images/hqd_grape.jpg"
            },
            {
                "category": "Вейпы",
                "product_name": "Одноразовые",
                "product_full_name": "HQD Cuvie Plus",
                "flavor": "Ментол",
                "price": 950,
                "description": "Одноразовая электронная сигарета HQD Cuvie Plus с ёмкостью аккумулятора 550 мАч. До 1200 затяжек.",
                "quantity": random.randint(5, 20),
                "image_path": "images/hqd_menthol.jpg"
            },
            {
                "category": "Вейпы",
                "product_name": "Многоразовые",
                "product_full_name": "Smok Nord 4",
                "flavor": "Чёрный",
                "price": 3500,
                "description": "Популярный под-система с мощностью до 80 Вт и аккумулятором 2000 мАч. Картридж на 4.5 мл.",
                "quantity": random.randint(2, 10),
                "image_path": "images/smok_nord4_black.jpg"
            },
            {
                "category": "Вейпы",
                "product_name": "Многоразовые",
                "product_full_name": "Smok Nord 4",
                "flavor": "Красный",
                "price": 3500,
                "description": "Популярный под-система с мощностью до 80 Вт и аккумулятором 2000 мАч. Картридж на 4.5 мл.",
                "quantity": random.randint(2, 10),
                "image_path": "images/smok_nord4_red.jpg"
            },
            {
                "category": "Вейпы",
                "product_name": "Боксмоды",
                "product_full_name": "Voopoo Drag 3",
                "flavor": "Классик",
                "price": 5500,
                "description": "Мощный боксмод с максимальной мощностью 177 Вт и стильным дизайном. Работает на чипсете GENE.FAN 2.0.",
                "quantity": random.randint(1, 5),
                "image_path": "images/voopoo_drag3.jpg"
            },
        ]

        # Тестовые данные для жидкостей
        liquids = [
            {
                "category": "Жидкости",
                "product_name": "Солевые",
                "product_full_name": "Taboo Salt",
                "flavor": "Черника",
                "price": 450,
                "description": "Солевая жидкость с крепостью 20 мг/мл. Объём 30 мл.",
                "quantity": random.randint(10, 30),
                "image_path": "images/taboo_blueberry.jpg"
            },
            {
                "category": "Жидкости",
                "product_name": "Солевые",
                "product_full_name": "Taboo Salt",
                "flavor": "Манго",
                "price": 450,
                "description": "Солевая жидкость с крепостью 20 мг/мл. Объём 30 мл.",
                "quantity": random.randint(10, 30),
                "image_path": "images/taboo_mango.jpg"
            },
            {
                "category": "Жидкости",
                "product_name": "Солевые",
                "product_full_name": "Smoke Kitchen Salt",
                "flavor": "Яблоко",
                "price": 550,
                "description": "Солевая жидкость с крепостью 50 мг/мл. Объём 30 мл.",
                "quantity": random.randint(10, 30),
                "image_path": "images/smoke_kitchen_apple.jpg"
            },
            {
                "category": "Жидкости",
                "product_name": "Солевые",
                "product_full_name": "Smoke Kitchen Salt",
                "flavor": "Клубника",
                "price": 550,
                "description": "Солевая жидкость с крепостью 50 мг/мл. Объём 30 мл.",
                "quantity": random.randint(10, 30),
                "image_path": "images/smoke_kitchen_strawberry.jpg"
            },
            {
                "category": "Жидкости",
                "product_name": "Обычные",
                "product_full_name": "Chew",
                "flavor": "Жвачка",
                "price": 350,
                "description": "Классическая жидкость для ежедневного парения с крепостью 3 мг/мл. Объём 60 мл.",
                "quantity": random.randint(10, 30),
                "image_path": "images/chew_gum.jpg"
            },
            {
                "category": "Жидкости",
                "product_name": "Обычные",
                "product_full_name": "Chew",
                "flavor": "Кола",
                "price": 350,
                "description": "Классическая жидкость для ежедневного парения с крепостью 3 мг/мл. Объём 60 мл.",
                "quantity": random.randint(10, 30),
                "image_path": "images/chew_cola.jpg"
            },
            {
                "category": "Жидкости",
                "product_name": "Премиум",
                "product_full_name": "Bad Drip",
                "flavor": "Cereal Trip",
                "price": 950,
                "description": "Премиальная жидкость с Вкусом хлопьев и молока. Крепость 3 мг/мл. Объём 60 мл.",
                "quantity": random.randint(5, 15),
                "image_path": "images/bad_drip_cereal.jpg"
            },
            {
                "category": "Жидкости",
                "product_name": "Премиум",
                "product_full_name": "Bad Drip",
                "flavor": "God Nectar",
                "price": 950,
                "description": "Премиальная жидкость с Вкусом экзотических фруктов. Крепость 3 мг/мл. Объём 60 мл.",
                "quantity": random.randint(5, 15),
                "image_path": "images/bad_drip_nectar.jpg"
            },
        ]

        # Тестовые данные для аксессуаров
        accessories = [
            {
                "category": "Аксессуары",
                "product_name": "Комплектующие",
                "product_full_name": "Испаритель GTX Mesh Coil",
                "flavor": "0.6 Ом",
                "price": 250,
                "description": "Сменный испаритель для Vaporesso GTX. Рекомендуемая мощность 20-30 Вт.",
                "quantity": random.randint(15, 50),
                "image_path": "images/gtx_coil_0.6.jpg"
            },
            {
                "category": "Аксессуары",
                "product_name": "Комплектующие",
                "product_full_name": "Испаритель GTX Mesh Coil",
                "flavor": "0.2 Ом",
                "price": 250,
                "description": "Сменный испаритель для Vaporesso GTX. Рекомендуемая мощность 45-60 Вт.",
                "quantity": random.randint(15, 50),
                "image_path": "images/gtx_coil_0.2.jpg"
            },
            {
                "category": "Аксессуары",
                "product_name": "Хлопок",
                "product_full_name": "Вата Cotton Bacon",
                "flavor": "Prime",
                "price": 350,
                "description": "Высококачественная органическая вата для спиралей. Не содержит пестицидов и бличей.",
                "quantity": random.randint(10, 30),
                "image_path": "images/cotton_bacon.jpg"
            },
            {
                "category": "Аксессуары",
                "product_name": "Хлопок",
                "product_full_name": "Вата Kendo Gold",
                "flavor": "Стандарт",
                "price": 300,
                "description": "Японский органический хлопок премиум-класса для намотки спиралей.",
                "quantity": random.randint(10, 30),
                "image_path": "images/kendo_gold.jpg"
            },
        ]

        # Добавляем все данные в базу
        all_products = vapes + liquids + accessories

        for product in all_products:
            cursor.execute('''
            INSERT INTO products
            (category, product_name, product_full_name, flavor, price, description, quantity, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product["category"],
                product["product_name"],
                product["product_full_name"],
                product["flavor"],
                product["price"],
                product["description"],
                product["quantity"],
                product["image_path"]
            ))

        conn.commit()
        print(f"База данных успешно заполнена {len(all_products)} товарами.")

    except sqlite3.Error as e:
        print(f"Ошибка при заполнении базы данных: {e}")




def main():
    conn = create_connection()
    if conn:
        create_tables(conn)
        seed_data(conn)
        conn.close()
        print("Заполнение базы данных завершено успешно.")
    else:
        print("Не удалось подключиться к базе данных.")


if __name__ == "__main__":
    main()
