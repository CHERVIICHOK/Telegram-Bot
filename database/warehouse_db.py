import sqlite3


class WarehouseDatabase:
    def __init__(self, db_file="warehouse.db"):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def get_all_categories(self) -> list[str]:
        """Возвращает список уникальных категорий (строки)."""
        self.cursor.execute("SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category")
        # Преобразуем список кортежей [('Cat1',), ('Cat2',)] в список строк ['Cat1', 'Cat2']
        return [row[0] for row in self.cursor.fetchall()]

    def get_product_names_by_category(self, category: str) -> list[str]:
        """Возвращает список уникальных названий продуктов для категории (строки)."""
        self.cursor.execute("""
            SELECT DISTINCT product_name FROM products 
            WHERE category = ? AND is_active = 1 
            ORDER BY product_name
        """, (category,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_flavors_by_product_name(self, product_name: str) -> list[tuple[int, str]]:
        """Возвращает список вкусов (ID и полное имя) для названия продукта."""
        self.cursor.execute("""
            SELECT id, product_full_name FROM products 
            WHERE product_name = ? AND is_active = 1 
            ORDER BY flavor
        """, (product_name,))
        return self.cursor.fetchall()

    def get_product_name_by_id(self, product_id: int) -> str | None:
        """Возвращает полное имя продукта по его ID."""
        self.cursor.execute("SELECT product_full_name FROM products WHERE id = ?", (product_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def close(self):
        self.connection.close()
