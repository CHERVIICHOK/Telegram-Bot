from typing import Dict, Tuple, Optional


class CatalogMapping:
    """Менеджер для маппинга названий категорий и товаров на короткие ID"""

    def __init__(self):
        self._category_to_id: Dict[str, str] = {}
        self._id_to_category: Dict[str, str] = {}
        self._product_to_id: Dict[Tuple[str, str], str] = {}
        self._id_to_product: Dict[str, Tuple[str, str]] = {}
        self._counter = 0

    def get_category_id(self, category_name: str) -> str:
        """Получает или создает ID для категории"""
        if category_name not in self._category_to_id:
            self._counter += 1
            cat_id = f"c{self._counter}"
            self._category_to_id[category_name] = cat_id
            self._id_to_category[cat_id] = category_name
        return self._category_to_id[category_name]

    def get_category_name(self, category_id: str) -> Optional[str]:
        """Получает название категории по ID"""
        return self._id_to_category.get(category_id)

    def get_product_id(self, category_name: str, product_name: str) -> str:
        """Получает или создает ID для пары (категория, товар)"""
        key = (category_name, product_name)
        if key not in self._product_to_id:
            self._counter += 1
            prod_id = f"p{self._counter}"
            self._product_to_id[key] = prod_id
            self._id_to_product[prod_id] = key
        return self._product_to_id[key]

    def get_product_info(self, product_id: str) -> Optional[Tuple[str, str]]:
        """Получает (категория, товар) по ID"""
        return self._id_to_product.get(product_id)

    def clear(self):
        """Очищает все маппинги"""
        self._category_to_id.clear()
        self._id_to_category.clear()
        self._product_to_id.clear()
        self._id_to_product.clear()
        self._counter = 0


# Глобальный экземпляр маппинга
catalog_mapping = CatalogMapping()