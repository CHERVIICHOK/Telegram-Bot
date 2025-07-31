import logging
import sqlite3

DATABASE = 'shop_bot.db'

logger = logging.getLogger(__name__)


def get_db_connection():
    """Создает соединение с базой данных shop_bot.db"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_staff_table():
    """Создает таблицу staff если она не существует"""
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT NOT NULL,
                last_name TEXT,
                phone TEXT,
                role TEXT NOT NULL,  -- 'admin', 'courier'
                access_level INTEGER NOT NULL DEFAULT 1,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        conn.commit()
        logger.info("Таблица staff создана или уже существует")
        return True
    except Exception as e:
        logger.error(f"FAIL: Ошибка при создании таблицы staff: {e}")
        return False
    finally:
        conn.close()


def get_staff_by_role(role=None):
    """Получение списка сотрудников по роли"""
    conn = get_db_connection()
    try:
        if role:
            query = "SELECT * FROM staff WHERE role = ? AND is_active = 1 ORDER BY first_name"
            rows = conn.execute(query, (role,)).fetchall()
        else:
            query = "SELECT * FROM staff WHERE is_active = 1 ORDER BY role, first_name"
            rows = conn.execute(query).fetchall()

        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"FAIL: Ошибка при получении сотрудников по роли: {e}")
        return []
    finally:
        conn.close()


def get_all_active_staff():
    """Получение всех активных сотрудников"""
    conn = get_db_connection()
    try:
        query = "SELECT * FROM staff WHERE is_active = 1 ORDER BY role, first_name"
        rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"FAIL: Ошибка при получении всех активных сотрудников: {e}")
        return []
    finally:
        conn.close()


def get_staff_by_id(staff_id):
    """Получение данных конкретного сотрудника по ID"""
    conn = get_db_connection()
    try:
        query = "SELECT * FROM staff WHERE id = ?"
        row = conn.execute(query, (staff_id,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"FAIL: Ошибка при получении сотрудника по ID: {e}")
        return None
    finally:
        conn.close()


def get_staff_by_telegram_id(telegram_id):
    """Получение данных сотрудника по Telegram ID"""
    conn = get_db_connection()
    try:
        query = "SELECT * FROM staff WHERE telegram_id = ?"
        row = conn.execute(query, (telegram_id,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"FAIL: Ошибка при получении сотрудника по Telegram ID: {e}")
        return None
    finally:
        conn.close()


def add_staff_member(telegram_id, username, first_name, last_name=None, phone=None, role="courier", access_level=1):
    """Добавление нового сотрудника"""
    conn = get_db_connection()
    try:
        query = """
            INSERT INTO staff (telegram_id, username, first_name, last_name, phone, role, access_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        conn.execute(query, (telegram_id, username, first_name, last_name, phone, role, access_level))
        conn.commit()
        logger.info(f"Добавлен новый сотрудник: {first_name} {last_name or ''} с ролью {role}")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"FAIL: Сотрудник с Telegram ID {telegram_id} уже существует: {e}")
        return False
    except Exception as e:
        logger.error(f"FAIL: Ошибка при добавлении сотрудника: {e}")
        return False
    finally:
        conn.close()


def update_staff_role(staff_id, new_role):
    """Обновление роли сотрудника"""
    conn = get_db_connection()
    try:
        query = "UPDATE staff SET role = ? WHERE id = ?"
        conn.execute(query, (new_role, staff_id))
        conn.commit()
        logger.info(f"Обновлена роль сотрудника ID {staff_id} на {new_role}")
        return True
    except Exception as e:
        logger.error(f"FAIL: Ошибка при обновлении роли сотрудника: {e}")
        return False
    finally:
        conn.close()


def update_staff_access_level(staff_id, new_level):
    """Обновление уровня доступа сотрудника"""
    conn = get_db_connection()
    try:
        query = "UPDATE staff SET access_level = ? WHERE id = ?"
        conn.execute(query, (new_level, staff_id))
        conn.commit()
        logger.info(f"Обновлен уровень доступа сотрудника ID {staff_id} на {new_level}")
        return True
    except Exception as e:
        logger.error(f"FAIL: Ошибка при обновлении уровня доступа сотрудника: {e}")
        return False
    finally:
        conn.close()


def toggle_staff_status(staff_id):
    """Изменение статуса активности сотрудника"""
    conn = get_db_connection()
    try:
        # Сначала получаем текущий статус
        query_get = "SELECT is_active FROM staff WHERE id = ?"
        current_status = conn.execute(query_get, (staff_id,)).fetchone()

        if current_status is None:
            logger.error(f"FAIL: Сотрудник с ID {staff_id} не найден")
            return False

        # Инвертируем статус
        new_status = 0 if current_status['is_active'] else 1
        status_text = "деактивирован" if new_status == 0 else "активирован"

        # Обновляем статус
        query_update = "UPDATE staff SET is_active = ? WHERE id = ?"
        conn.execute(query_update, (new_status, staff_id))
        conn.commit()

        logger.info(f"Статус сотрудника ID {staff_id} {status_text}")
        return True
    except Exception as e:
        logger.error(f"FAIL: Ошибка при изменении статуса сотрудника: {e}")
        return False
    finally:
        conn.close()


def delete_staff_member(staff_id):
    """Удаление сотрудника"""
    conn = get_db_connection()
    try:
        query = "DELETE FROM staff WHERE id = ?"
        conn.execute(query, (staff_id,))
        conn.commit()
        logger.info(f"Удален сотрудник ID {staff_id}")
        return True
    except Exception as e:
        logger.error(f"FAIL: Ошибка при удалении сотрудника: {e}")
        return False
    finally:
        conn.close()


def update_staff_last_login(telegram_id):
    """Обновление времени последнего входа сотрудника"""
    conn = get_db_connection()
    try:
        query = "UPDATE staff SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?"
        conn.execute(query, (telegram_id,))
        conn.commit()
        logger.info(f"Обновлено время последнего входа для сотрудника с Telegram ID {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"FAIL: Ошибка при обновлении времени последнего входа: {e}")
        return False
    finally:
        conn.close()


def get_staff_roles():
    """Получение списка всех уникальных ролей в системе"""
    return get_all_available_roles()


def get_all_staff_statuses():
    """Получает все уникальные роли (статусы) сотрудников из БД"""
    conn = get_db_connection()
    try:
        query = "SELECT DISTINCT role FROM staff ORDER BY role"
        rows = conn.execute(query).fetchall()
        return [row['role'] for row in rows]
    except Exception as e:
        logger.error(f"FAIL: Ошибка при получении списка ролей сотрудников: {e}")
        return []
    finally:
        conn.close()


def add_new_staff_status(status_name, status_description=None):
    """
    Добавляет новую роль (статус) сотрудника

    Для реализации добавления новой роли, мы создаем отдельную таблицу,
    которая хранит информацию о доступных ролях и их описаниях.
    """
    conn = get_db_connection()
    try:
        # Проверяем, существует ли таблица с ролями
        conn.execute('''
            CREATE TABLE IF NOT EXISTS staff_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Проверяем, нет ли уже такой роли
        existing = conn.execute("SELECT * FROM staff_roles WHERE role_name = ?",
                                (status_name,)).fetchone()

        if existing:
            logger.warning(f"Роль '{status_name}' уже существует")
            return False, "Такая роль уже существует"

        # Добавляем новую роль
        conn.execute("INSERT INTO staff_roles (role_name, description) VALUES (?, ?)",
                     (status_name, status_description))
        conn.commit()

        logger.info(f"Создана новая роль сотрудника: {status_name}")
        return True, "Роль успешно создана"
    except Exception as e:
        logger.error(f"FAIL: Ошибка при создании новой роли сотрудника: {e}")
        return False, f"Ошибка: {str(e)}"
    finally:
        conn.close()


def get_staff_status_details(status_name):
    """Получает детальную информацию о статусе (роли) сотрудника"""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM staff_roles WHERE role_name = ?",
                           (status_name,)).fetchone()

        if row:
            return dict(row)

        # Если роль не найдена в таблице staff_roles,
        # но используется в таблице staff, создаем запись "по факту"
        count = conn.execute("SELECT COUNT(*) as count FROM staff WHERE role = ?",
                             (status_name,)).fetchone()['count']

        if count > 0:
            return {
                'role_name': status_name,
                'description': 'Автоматически созданная роль',
                'count': count
            }

        return None
    except Exception as e:
        logger.error(f"FAIL: Ошибка при получении деталей роли: {e}")
        return None
    finally:
        conn.close()


def get_all_available_roles():
    """
    Получает полный список доступных ролей, включая:
    1) Роли из таблицы staff (которые уже используются сотрудниками)
    2) Роли из таблицы staff_roles (которые могут еще не использоваться)
    """
    conn = get_db_connection()
    try:
        # Проверяем существование таблицы staff_roles
        try:
            conn.execute("SELECT 1 FROM staff_roles LIMIT 1")
            staff_roles_exists = True
        except sqlite3.OperationalError:
            staff_roles_exists = False

        # Получаем роли из таблицы staff
        roles_from_staff = set([row['role'] for row in
                                conn.execute("SELECT DISTINCT role FROM staff").fetchall()])

        # Если таблица staff_roles существует, получаем роли оттуда
        if staff_roles_exists:
            roles_from_roles_table = set([row['role_name'] for row in
                                          conn.execute("SELECT DISTINCT role_name FROM staff_roles").fetchall()])

            # Объединяем уникальные роли из обеих таблиц
            all_roles = list(roles_from_staff.union(roles_from_roles_table))
        else:
            all_roles = list(roles_from_staff)

        # Сортируем роли по алфавиту
        all_roles.sort()

        # Если список пуст, возвращаем стандартные роли
        if not all_roles:
            return ["Администратор", "Курьер", "Менеджер", "Консультант"]

        return all_roles
    except Exception as e:
        logger.error(f"FAIL: Ошибка при получении списка всех ролей: {e}")
        return ["Администратор", "Курьер", "Менеджер", "Консультант"]
    finally:
        conn.close()
