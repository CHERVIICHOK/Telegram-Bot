import sqlite3
import datetime


class DiscountsDatabase:
    def __init__(self, db_file="discounts.db"):
        """Инициализация соединения с базой данных."""
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        """Создание таблиц, если они не существуют."""
        with self.connection:
            # Таблица промокодов
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    description TEXT,
                    discount_type TEXT NOT NULL CHECK(discount_type IN ('percentage', 'fixed_amount')),
                    discount_value REAL NOT NULL,
                    min_order_amount REAL DEFAULT 0,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    max_uses INTEGER DEFAULT 999999,
                    current_uses INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_by_id INTEGER,
                    created_by_username TEXT
                )
            """)
            # Таблица использования промокодов
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS promo_code_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_code_id INTEGER,
                    user_id INTEGER NOT NULL,
                    order_id INTEGER,
                    used_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    discount_amount REAL NOT NULL,
                    order_total REAL NOT NULL,
                    FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id)
                )
            """)
            # Таблица "Товар дня"
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    description TEXT,
                    discount_type TEXT NOT NULL CHECK(discount_type IN ('percentage', 'fixed_amount')),
                    discount_value REAL NOT NULL,
                    deal_date TEXT NOT NULL UNIQUE,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Таблица использования "Товара дня" (может быть полезна для аналитики)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_deal_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    daily_deal_id INTEGER,
                    user_id INTEGER NOT NULL,
                    order_id INTEGER NOT NULL,
                    used_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    discount_amount REAL NOT NULL,
                    order_total REAL NOT NULL,
                    FOREIGN KEY (daily_deal_id) REFERENCES daily_deals(id)
                )
            """)
            # Таблица просмотров промокодов
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS promo_code_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_code_id INTEGER,
                    user_id INTEGER NOT NULL,
                    viewed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id)
                )
            """)
            # Таблица категорий для промокодов
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS promo_product_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_code_id INTEGER,
                    category TEXT NOT NULL,
                    FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id)
                )
            """)

            self.cursor.execute("DROP TABLE IF EXISTS daily_deals")
            self.cursor.execute("DROP TABLE IF EXISTS daily_deal_usage")

            self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS actions (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                title TEXT NOT NULL,
                                description TEXT NOT NULL,
                                product_id INTEGER, -- Необязательное поле
                                discount_type TEXT NOT NULL CHECK(discount_type IN ('percentage', 'fixed_amount')),
                                discount_value REAL NOT NULL,
                                start_date TEXT NOT NULL,
                                end_date TEXT NOT NULL,
                                is_active BOOLEAN NOT NULL DEFAULT 1,
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                created_by_id INTEGER,
                                created_by_username TEXT
                            )
                        """)

    def add_dummy_data(self):
        """Добавление тестовых данных для демонстрации."""
        try:
            with self.connection:
                # Добавляем промокоды
                today = datetime.date.today()
                end_date = today + datetime.timedelta(days=30)

                promos = [
                    ('SUMMER10', 'Скидка 10% на все заказы от 1500 руб.', 'percentage', 10.0, 1500.0, today.isoformat(),
                     end_date.isoformat(), 1, 100, 5),
                    ('NEWBIE', 'Скидка 300 руб. для новых пользователей.', 'fixed_amount', 300.0, 1000.0,
                     today.isoformat(), end_date.isoformat(), 1, 50, 0),
                    ('EXPIRED', 'Просроченный промокод', 'percentage', 20.0, 0, '2020-01-01', '2020-01-31', 1, 10, 2)
                ]
                self.cursor.executemany("""
                    INSERT INTO promo_codes (code, description, discount_type, discount_value, min_order_amount, start_date, end_date, is_active, max_uses, current_uses) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, promos)

                # Добавляем "Товар дня"
                deal_date_str = today.isoformat()
                self.cursor.execute("""
                    INSERT INTO daily_deals (product_id, description, discount_type, discount_value, deal_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (123, 'Скидка 20% на жидкость "Husky"', 'percentage', 20.0, deal_date_str, 1))

        except sqlite3.IntegrityError:
            # Данные уже существуют
            pass

    def get_active_promo_codes(self):
        """Получение списка активных промокодов."""
        today = datetime.date.today().isoformat()
        self.cursor.execute("""
            SELECT id, code, description, discount_type, discount_value, min_order_amount
            FROM promo_codes
            WHERE is_active = 1
              AND current_uses < max_uses
              AND date(start_date) <= ?
              AND date(end_date) >= ?
        """, (today, today))
        return self.cursor.fetchall()

    def get_promo_code_details(self, promo_id: int):
        """Получение деталей конкретного промокода по ID."""
        self.cursor.execute("SELECT * FROM promo_codes WHERE id = ?", (promo_id,))
        return self.cursor.fetchone()

    def log_promo_view(self, promo_id: int, user_id: int):
        """Логирование просмотра промокода."""
        with self.connection:
            self.cursor.execute(
                "INSERT INTO promo_code_views (promo_code_id, user_id) VALUES (?, ?)",
                (promo_id, user_id)
            )

    def get_daily_deal(self):
        """Получение 'Товара дня' на сегодня."""
        today_date = datetime.date.today().isoformat()
        self.cursor.execute("""
            SELECT product_id, description, discount_type, discount_value
            FROM daily_deals
            WHERE deal_date = ? AND is_active = 1
        """, (today_date,))
        return self.cursor.fetchone()

    def validate_promo_code(self, code_text: str):
        """Проверка промокода на валидность."""
        self.cursor.execute("SELECT * FROM promo_codes WHERE code = ?", (code_text,))
        promo = self.cursor.fetchone()

        if not promo:
            return None, "Промокод не найден."

        # Преобразуем поля в более удобный формат
        promo_dict = {
            'id': promo[0], 'code': promo[1], 'description': promo[2],
            'discount_type': promo[3], 'discount_value': promo[4],
            'min_order_amount': promo[5], 'start_date': promo[6],
            'end_date': promo[7], 'is_active': promo[8], 'max_uses': promo[9],
            'current_uses': promo[10]
        }

        today = datetime.date.today().isoformat()

        if not promo_dict['is_active']:
            return None, "Этот промокод больше не активен."
        if promo_dict['current_uses'] >= promo_dict['max_uses']:
            return None, "К сожалению, лимит использования этого промокода исчерпан."
        if promo_dict['start_date'] > today:
            return None, "Срок действия этого промокода еще не начался."
        if promo_dict['end_date'] < today:
            return None, "Срок действия этого промокода уже истек."

        return promo_dict, "Промокод успешно применен!"

    def add_promo_code(self, data: dict):
        """Добавляет новый промокод в базу данных."""
        with self.connection:
            self.cursor.execute("""
                INSERT INTO promo_codes (
                    code, description, discount_type, discount_value, 
                    min_order_amount, start_date, end_date, max_uses, 
                    is_active, created_by_id, created_by_username
                )
                VALUES (
                    :code, :description, :discount_type, :discount_value, 
                    :min_order_amount, :start_date, :end_date, :max_uses, 
                    1, :created_by_id, :created_by_username
                )
            """, data)

    def get_all_promo_codes(self, include_inactive=True):
        """Получение списка всех промокодов для админки."""
        query = "SELECT id, code, is_active, current_uses, max_uses, end_date FROM promo_codes ORDER BY created_at DESC"
        if not include_inactive:
            query = "SELECT id, code, is_active, current_uses, max_uses, end_date FROM promo_codes WHERE is_active = 1 ORDER BY created_at DESC"

        self.cursor.execute(query)
        return self.cursor.fetchall()

    def update_promo_code_status(self, promo_id: int, is_active: bool):
        """Изменяет статус активности промокода."""
        with self.connection:
            self.cursor.execute("UPDATE promo_codes SET is_active = ? WHERE id = ?", (is_active, promo_id))

    def delete_promo_code(self, promo_id: int):
        """Удаляет промокод и связанные с ним данные."""
        with self.connection:
            # Сначала удаляем связанные данные, чтобы не нарушать внешние ключи
            self.cursor.execute("DELETE FROM promo_code_usage WHERE promo_code_id = ?", (promo_id,))
            self.cursor.execute("DELETE FROM promo_code_views WHERE promo_code_id = ?", (promo_id,))
            self.cursor.execute("DELETE FROM promo_product_categories WHERE promo_code_id = ?", (promo_id,))
            # Затем удаляем сам промокод
            self.cursor.execute("DELETE FROM promo_codes WHERE id = ?", (promo_id,))

    def add_or_update_daily_deal(self, data: dict):
        """Создает или обновляет 'Товар дня' для указанной даты."""
        with self.connection:
            # Проверяем, есть ли уже запись на эту дату
            self.cursor.execute("SELECT id FROM daily_deals WHERE deal_date = ?", (data['deal_date'],))
            existing_deal = self.cursor.fetchone()

            if existing_deal:
                # Обновляем
                self.cursor.execute("""
                    UPDATE daily_deals 
                    SET product_id = :product_id, description = :description, discount_type = :discount_type, discount_value = :discount_value, is_active = 1
                    WHERE deal_date = :deal_date
                """, data)
            else:
                # Создаем
                self.cursor.execute("""
                    INSERT INTO daily_deals (product_id, description, discount_type, discount_value, deal_date, is_active)
                    VALUES (:product_id, :description, :discount_type, :discount_value, :deal_date, 1)
                """, data)

    def delete_daily_deal(self, deal_date: str):
        """Удаляет 'Товар дня' на определенную дату."""
        with self.connection:
            self.cursor.execute("DELETE FROM daily_deals WHERE deal_date = ?", (deal_date,))

    def get_promo_code_by_code(self, code: str):
        """Возвращает промокод по его текстовому коду."""
        self.cursor.execute("SELECT * FROM promo_codes WHERE code = ?", (code,))
        return self.cursor.fetchone()

    def add_action(self, data: dict):
        """Добавляет новую акцию в базу данных."""
        with self.connection:
            self.cursor.execute("""
                   INSERT INTO actions (title, description, product_id, discount_type, discount_value, start_date, end_date, is_active, created_by_id, created_by_username)
                   VALUES (:title, :description, :product_id, :discount_type, :discount_value, :start_date, :end_date, 1, :created_by_id, :created_by_username)
               """, data)

    def get_all_actions(self):
        """Получает все акции, сортируя их по дате окончания."""
        self.cursor.execute("SELECT id, title, start_date, end_date, is_active FROM actions ORDER BY end_date DESC")
        return self.cursor.fetchall()

    def get_action_details(self, action_id: int):
        """Получает полную информацию об акции по ее ID."""
        self.cursor.execute("SELECT * FROM actions WHERE id = ?", (action_id,))
        return self.cursor.fetchone()

    def update_action_status(self, action_id: int, is_active: bool):
        """Изменяет статус активности акции."""
        with self.connection:
            self.cursor.execute("UPDATE actions SET is_active = ? WHERE id = ?", (is_active, action_id))

    def delete_action(self, action_id: int):
        """Удаляет акцию."""
        with self.connection:
            self.cursor.execute("DELETE FROM actions WHERE id = ?", (action_id,))

        # --- МЕТОДЫ ДЛЯ АКЦИЙ (КЛИЕНТ) ---

    def get_active_actions(self):
        """Получает список активных на данный момент акций для клиентов."""
        today = datetime.date.today().isoformat()
        self.cursor.execute("""
               SELECT title, description, discount_type, discount_value, end_date
               FROM actions
               WHERE is_active = 1
                 AND date(start_date) <= ?
                 AND date(end_date) >= ?
               ORDER BY end_date ASC
           """, (today, today))
        return self.cursor.fetchall()

    def close(self):
        """Закрытие соединения с БД."""
        self.connection.close()

    def check_user_promo_usage(self, promo_code_id: int, user_id: int):
        """Проверяет, использовал ли пользователь данный промокод ранее."""
        self.cursor.execute("""
            SELECT COUNT(*) FROM promo_code_usage 
            WHERE promo_code_id = ? AND user_id = ?
        """, (promo_code_id, user_id))

        count = self.cursor.fetchone()[0]
        return count > 0

    def validate_promo_code_for_user(self, code_text: str, user_id: int):
        """Проверка промокода на валидность с учетом использования конкретным пользователем."""
        self.cursor.execute("SELECT * FROM promo_codes WHERE code = ?", (code_text,))
        promo = self.cursor.fetchone()

        if not promo:
            return None, "Промокод не найден."

        # Преобразуем поля в более удобный формат
        promo_dict = {
            'id': promo[0], 'code': promo[1], 'description': promo[2],
            'discount_type': promo[3], 'discount_value': promo[4],
            'min_order_amount': promo[5], 'start_date': promo[6],
            'end_date': promo[7], 'is_active': promo[8], 'max_uses': promo[9],
            'current_uses': promo[10]
        }

        today = datetime.date.today().isoformat()

        if not promo_dict['is_active']:
            return None, "Этот промокод больше не активен."
        if promo_dict['current_uses'] >= promo_dict['max_uses']:
            return None, "К сожалению, лимит использования этого промокода исчерпан."
        if promo_dict['start_date'] > today:
            return None, "Срок действия этого промокода еще не начался."
        if promo_dict['end_date'] < today:
            return None, "Срок действия этого промокода уже истек."

        # Проверяем, использовал ли пользователь этот промокод ранее
        if self.check_user_promo_usage(promo_dict['id'], user_id):
            return None, "Вы уже использовали этот промокод ранее."

        return promo_dict, "Промокод успешно применен!"

    def get_active_actions_for_products(self, cart_items):
        """Получает активные акции, применимые к товарам в корзине."""
        today = datetime.date.today().isoformat()

        applicable_actions = []

        # Получаем все активные акции
        self.cursor.execute("""
            SELECT id, title, description, product_id, discount_type, discount_value
            FROM actions
            WHERE is_active = 1
              AND date(start_date) <= ?
              AND date(end_date) >= ?
        """, (today, today))

        active_actions = self.cursor.fetchall()

        for action in active_actions:
            action_id, title, description, product_id, discount_type, discount_value = action

            # Если акция на конкретный товар
            if product_id:
                for item in cart_items:
                    if item['product_id'] == product_id:
                        applicable_actions.append({
                            'action_id': action_id,
                            'title': title,
                            'description': description,
                            'product_id': product_id,
                            'discount_type': discount_type,
                            'discount_value': discount_value,
                            'applicable_items': [item],
                            'scope': 'product'
                        })
            else:
                # Акция на категорию или линейку (определяем по описанию)
                # Для простоты будем считать, что если product_id = NULL, то акция на все товары
                applicable_actions.append({
                    'action_id': action_id,
                    'title': title,
                    'description': description,
                    'product_id': None,
                    'discount_type': discount_type,
                    'discount_value': discount_value,
                    'applicable_items': cart_items,
                    'scope': 'all'
                })

        return applicable_actions

    def get_action_by_category_or_product_line(self, category=None, product_line=None):
        """Получает акции по категории или линейке товаров (для будущего расширения)."""
        today = datetime.date.today().isoformat()

        # Пока что возвращаем общие акции, в будущем можно расширить
        self.cursor.execute("""
            SELECT id, title, description, discount_type, discount_value
            FROM actions
            WHERE is_active = 1
              AND date(start_date) <= ?
              AND date(end_date) >= ?
              AND product_id IS NULL
        """, (today, today))

        return self.cursor.fetchall()
