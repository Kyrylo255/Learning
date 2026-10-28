
# ============================================================
# 1. ІМПОРТИ — підключаємо інструменти, які використовуємо
# ============================================================

import sys  # Потрібен для запуску та завершення програми

import psycopg  # Драйвер для роботи з PostgreSQL

# Інструменти PySide6 для інтерфейсу та таймера
from PySide6.QtCore import Qt, QTimer

from PySide6.QtWidgets import (
    QApplication,       # Запускає графічну програму
    QMainWindow,        # Головне вікно
    QWidget,            # Контейнер для елементів
    QVBoxLayout,        # Розміщення елементів вертикально
    QHBoxLayout,        # Розміщення елементів горизонтально
    QLabel,             # Текстові написи
    QPushButton,        # Кнопки
    QTableWidget,       # Таблиця
    QTableWidgetItem,   # Окрема комірка таблиці
    QMessageBox,        # Вікна повідомлень
    QHeaderView,        # Налаштування заголовків таблиці
    QMenu,              # Контекстне меню правої кнопки
    QDialog,            # Діалогове вікно
    QFormLayout,        # Форма з підписами та полями
    QLineEdit,          # Поле введення тексту
    QComboBox,          # Випадаючий список
    QDialogButtonBox,   # Кнопки збереження та скасування
)


# ============================================================
# 2. НАЛАШТУВАННЯ ПІДКЛЮЧЕННЯ ДО POSTGRESQL
# ============================================================

DB_CONFIG = {
    "host": "127.0.0.1",  # Адреса сервера БД на цьому комп'ютері
    "port": 5432,         # Стандартний порт PostgreSQL
    "dbname": "users_db", # Назва нашої бази даних
    "user": "postgres",   # Користувач PostgreSQL
    "password": "1234",   # Пароль для навчального середовища
}


# ============================================================
# 3. ФУНКЦІЇ ДЛЯ РОБОТИ З БАЗОЮ ДАНИХ
# ============================================================

def get_users():
    """Отримуємо користувачів із БД разом з їхніми ID."""

    # Відкриваємо з'єднання з PostgreSQL.
    # with автоматично закриє з'єднання після завершення блоку.
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # SQL-запит: отримуємо записи та сортуємо їх за ID.
            cur.execute("""
                SELECT id, username, password, role_name
                FROM users
                ORDER BY id;
            """)

            # fetchall() повертає всі рядки результату.
            return cur.fetchall()


def get_roles():
    """Отримуємо список доступних ролей із таблиці roles."""

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role_name
                FROM roles
                ORDER BY role_name;
            """)

            # Перетворюємо результат на список назв ролей.
            # Наприклад: ['DB engineer', 'Docker admin', 'admin', 'user']
            return [row[0] for row in cur.fetchall()]


def update_user(user_id, column, value):
    """Оновлюємо одну властивість конкретного користувача."""

    # Дозволяємо змінювати лише ці три поля.
    # Це не дає передати довільну назву стовпця в SQL.
    allowed_columns = {"username", "password", "role_name"}

    if column not in allowed_columns:
        raise ValueError("Недозволене поле")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # user_id визначає, який саме запис змінюємо.
            # %s — параметр SQL, значення передаються окремо.
            cur.execute(
                f"UPDATE users SET {column} = %s WHERE id = %s",
                (value, user_id),
            )

            if cur.rowcount == 0:
                raise ValueError("Користувача не знайдено")


def add_user(username, password, role_name):
    """Додаємо нового користувача в таблицю users."""

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, password, role_name)
                VALUES (%s, %s, %s);
            """, (username, password, role_name))


def delete_user(user_id):
    """Видаляємо користувача за його ID."""

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM users WHERE id = %s",
                (user_id,),
            )

            if cur.rowcount == 0:
                raise ValueError("Користувача не знайдено")


# ============================================================
# 4. ВІКНО ДОДАВАННЯ КОРИСТУВАЧА
# ============================================================

class AddUserDialog(QDialog):
    """Одна форма для введення логіна, пароля та ролі."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Додати користувача")
        self.setMinimumWidth(350)

        # Поле для логіна.
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Введи логін")

        # Поле для пароля.
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введи пароль")

        # Випадаючий список ролей із БД.
        self.role_combo = QComboBox()

        # Розміщуємо поля у формі.
        form = QFormLayout()
        form.addRow("Username:", self.username_input)
        form.addRow("Password:", self.password_input)
        form.addRow("Role:", self.role_combo)

        # Створюємо кнопки збереження та скасування.
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        self.buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setText("Зберегти")

        self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText("Скасувати")

        # Під'єднуємо натискання кнопок до функцій.
        self.buttons.accepted.connect(self.validate_form)
        self.buttons.rejected.connect(self.reject)

        # Збираємо всі елементи у вікно.
        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

        # Завантажуємо ролі з PostgreSQL.
        try:
            roles = get_roles()
            self.role_combo.addItems(roles)

        except Exception as error:
            QMessageBox.critical(
                self,
                "Помилка",
                f"Не вдалося завантажити ролі:\n{error}",
            )

        # Одразу ставимо курсор у поле логіна.
        self.username_input.setFocus()

    def validate_form(self):
        """Перевіряємо введені дані перед збереженням."""

        if not self.username_input.text().strip():
            QMessageBox.warning(
                self, "Помилка", "Введи Username."
            )
            return

        if not self.password_input.text():
            QMessageBox.warning(
                self, "Помилка", "Введи Password."
            )
            return

        if self.role_combo.count() == 0:
            QMessageBox.warning(
                self, "Помилка", "У базі немає доступних ролей."
            )
            return

        # Якщо всі перевірки пройшли — закриваємо форму
        # зі статусом Accepted.
        self.accept()

    def get_data(self):
        """Повертаємо введені значення головному вікну."""

        return (
            self.username_input.text().strip(),
            self.password_input.text(),
            self.role_combo.currentText(),
        )


# ============================================================
# 5. ГОЛОВНЕ ВІКНО ПРОГРАМИ
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyDBManager")
        self.resize(1000, 650)

        # True означає, що програма сама заповнює таблицю.
        # У цей момент не потрібно записувати зміни назад у БД.
        self.loading = False

        # Зберігаємо останній отриманий стан таблиці з БД.
        # Це дозволяє не перемальовувати таблицю без потреби.
        self.last_users = None

        # Заголовок програми.
        title = QLabel("PyDBManager")
        title.setStyleSheet(
            "font-size: 26px; font-weight: bold; padding: 10px;"
        )

        # Тут показуємо стан підключення.
        self.status_label = QLabel("Підключення до PostgreSQL...")

        # Створюємо таблицю з чотирма стовпцями.
        # ID потрібен програмі для редагування та видалення.
        self.table = QTableWidget(0, 4)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Username",
            "Password",
            "Role",
        ])

        # Приховуємо ID від користувача.
        self.table.setColumnHidden(0, True)

        # Налаштовуємо вигляд і вибір рядків.
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        # Комірки редагуються подвійним кліком або клавішею F2.
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )

        # Рівномірно розподіляємо ширину стовпців.
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        # Вмикаємо меню при натисканні правою кнопкою миші.
        self.table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.table.customContextMenuRequested.connect(
            self.show_context_menu
        )

        # Кнопка "+" для додавання нового користувача.
        self.add_button = QPushButton("+")
        self.add_button.setFixedSize(42, 36)
        self.add_button.setToolTip("Додати користувача")
        self.add_button.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )
        self.add_button.clicked.connect(self.add_user_dialog)

        # Розміщуємо "+" справа внизу.
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.add_button)

        # Основне розташування елементів.
        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)
        layout.addLayout(bottom_layout)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        # Коли комірку відредаговано, викликаємо збереження в БД.
        self.table.itemChanged.connect(self.save_cell_change)

        # Одразу завантажуємо користувачів під час запуску.
        self.load_users()

        # Автоматично перевіряємо БД кожні 3 секунди.
        # 3000 — це інтервал у мілісекундах.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_for_changes)
        self.timer.start(3000)

    # --------------------------------------------------------
    # Завантаження даних з PostgreSQL до таблиці
    # --------------------------------------------------------
    def load_users(self, force=False):
        try:
            users = get_users()

            # Якщо дані не змінилися, нічого не перемальовуємо.
            if not force and users == self.last_users:
                return

            self.loading = True
            self.table.setRowCount(len(users))

            # Проходимо по кожному користувачу.
            for row_index, user in enumerate(users):

                # user містить: ID, логін, пароль, роль.
                for column_index, value in enumerate(user):
                    text = "" if value is None else str(value)
                    item = QTableWidgetItem(text)

                    # Забороняємо редагувати прихований ID.
                    if column_index == 0:
                        item.setFlags(
                            item.flags()
                            & ~Qt.ItemFlag.ItemIsEditable
                        )

                    self.table.setItem(
                        row_index,
                        column_index,
                        item,
                    )

            # Запам'ятовуємо актуальні дані.
            self.last_users = users

            self.status_label.setText(
                f"Підключено до users_db | Користувачів: {len(users)}"
            )

        except Exception as error:
            self.status_label.setText("Помилка підключення до БД")
            print(f"Помилка PostgreSQL: {error}")

        finally:
            # Після завершення заповнення таблиці
            # дозволяємо обробляти ручне редагування.
            self.loading = False

    # --------------------------------------------------------
    # Періодична перевірка змін у БД
    # --------------------------------------------------------
    def check_for_changes(self):
        # Не оновлюємо таблицю, поки користувач редагує комірку.
        if self.table.state() == QTableWidget.State.EditingState:
            return

        self.load_users()

    # --------------------------------------------------------
    # Збереження змін після редагування комірки
    # --------------------------------------------------------
    def save_cell_change(self, item):
        # Ігноруємо зміни, зроблені самою програмою
        # під час завантаження таблиці.
        if self.loading:
            return

        row = item.row()
        column = item.column()

        # Читаємо прихований ID поточного рядка.
        id_item = self.table.item(row, 0)
        if id_item is None:
            return

        user_id = int(id_item.text())
        value = item.text()

        # Відповідність стовпців таблиці стовпцям PostgreSQL.
        columns = {
            1: "username",
            2: "password",
            3: "role_name",
        }

        db_column = columns.get(column)
        if db_column is None:
            return

        # Забороняємо порожні значення.
        if not value.strip():
            QMessageBox.warning(
                self, "Помилка", "Поле не може бути порожнім."
            )
            self.load_users(force=True)
            return

        try:
            # Записуємо нове значення в PostgreSQL.
            update_user(user_id, db_column, value)

            # Змушуємо наступну перевірку перечитати дані.
            self.last_users = None

            self.status_label.setText(
                f"Зміни збережено | ID: {user_id}"
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Не вдалося зберегти зміни",
                str(error),
            )

            # Якщо БД відхилила зміни, відновлюємо її значення.
            self.load_users(force=True)

    # --------------------------------------------------------
    # Відкриття форми додавання користувача
    # --------------------------------------------------------
    def add_user_dialog(self):
        # Створюємо одне вікно з усіма полями.
        dialog = AddUserDialog(self)

        # Якщо натиснули "Скасувати", нічого не робимо.
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Отримуємо дані з форми.
        username, password, role_name = dialog.get_data()

        try:
            # Додаємо користувача до БД.
            add_user(username, password, role_name)

            # Перезавантажуємо таблицю.
            self.last_users = None
            self.load_users(force=True)

            self.status_label.setText(
                f"Користувача {username} додано"
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Не вдалося додати користувача",
                str(error),
            )

    # --------------------------------------------------------
    # Контекстне меню при натисканні правою кнопкою
    # --------------------------------------------------------
    def show_context_menu(self, position):
        item = self.table.itemAt(position)

        # Якщо натиснули не на комірку, меню не показуємо.
        if item is None:
            return

        # Виділяємо рядок, на якому натиснули.
        self.table.selectRow(item.row())

        menu = QMenu(self)
        delete_action = menu.addAction("Видалити")

        # Показуємо меню біля курсора.
        action = menu.exec(
            self.table.viewport().mapToGlobal(position)
        )

        # Якщо вибрали "Видалити", викликаємо відповідну функцію.
        if action == delete_action:
            self.delete_selected_user()

    # --------------------------------------------------------
    # Видалення вибраного користувача
    # --------------------------------------------------------
    def delete_selected_user(self):
        row = self.table.currentRow()

        if row < 0:
            return

        id_item = self.table.item(row, 0)
        username_item = self.table.item(row, 1)

        if id_item is None or username_item is None:
            return

        user_id = int(id_item.text())
        username = username_item.text()

        # Запитуємо підтвердження, щоб уникнути випадкового видалення.
        answer = QMessageBox.question(
            self,
            "Підтвердження",
            f"Видалити користувача «{username}»?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_user(user_id)

            self.last_users = None
            self.load_users(force=True)

            self.status_label.setText(
                f"Користувача {username} видалено"
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Не вдалося видалити користувача",
                str(error),
            )


# ============================================================
# 6. ТОЧКА ВХОДУ — ЗАПУСК ПРОГРАМИ
# ============================================================

if __name__ == "__main__":
    # Створюємо графічний застосунок.
    app = QApplication(sys.argv)

    # Створюємо головне вікно.
    window = MainWindow()

    # Показуємо вікно на екрані.
    window.show()

    # Запускаємо цикл обробки подій.
    # Він дозволяє реагувати на кліки, введення тексту тощо.
    sys.exit(app.exec())
