import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import re
import time

# =====================================================================
# БЛОК 1: НАСТРОЙКА БАЗЫ ДАННЫХ (SQLite)
# =====================================================================

def init_db():
    conn = sqlite3.connect('food_delivery.db')
    cursor = conn.cursor()
    
    # Таблица ролей
    cursor.execute('''CREATE TABLE IF NOT EXISTS roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL)''')
    
    cursor.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Администратор')")
    cursor.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Клиент')")
    
    # Таблица пользователей (Специфичное поле: phone)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        role_id INTEGER NOT NULL,
                        FOREIGN KEY(role_id) REFERENCES roles(id))''')
    
    # Аккаунт администратора по умолчанию
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("""INSERT INTO users (username, password, email, phone, role_id) 
                          VALUES ('admin', 'Admin123!', 'manager@delivery.com', '+79991112233', 1)""")
    
    # Сущность 1: Меню блюд
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        price REAL NOT NULL,
                        category TEXT NOT NULL)''')
    
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone() == 0:
        cursor.executemany("INSERT INTO menu (name, price, category) VALUES (?, ?, ?)", [
            ('Пицца Маргарита', 450.0, 'Пицца'),
            ('Бургер Классический', 320.0, 'Бургеры'),
            ('Суши Филадельфия', 590.0, 'Суши')
        ])

    # Сущность 2: Заказы
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        address TEXT NOT NULL,
                        status TEXT NOT NULL,
                        total_price REAL NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Сущность 3: Содержимое заказов (Связующая таблица)
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        menu_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
                        FOREIGN KEY(menu_id) REFERENCES menu(id))''')
    
    conn.commit()
    conn.close()

# =====================================================================
# БЛОК 2: ВАЛИДАЦИЯ ДАННЫХ
# =====================================================================

def validate_email(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(regex, email):
        return False
    
    # Хитрое исключение по ТЗ: admin запрещен в домене после @
    parts = email.split('@')
    if len(parts) == 2 and 'admin' in parts[1].lower():
        return False
    return True

def validate_password(password):
    if len(password) < 8: 
        return False
    if not any(c.isupper() for c in password): 
        return False
    if not any(c.isdigit() for c in password): 
        return False
    
    specials = "!@#$%^&*()-_=+[{]};:'\",<.>/?`~"
    if not any(c in specials for c in password): 
        return False
        
    return True
# =====================================================================
# БЛОК 3: ОКНА АВТОРИЗАЦИИ И РЕГИСТРАЦИИ
# =====================================================================

class AuthScreens:
    def __init__(self, app):
        self.app = app
        self.failed_attempts = 0
        self.lock_until = 0

    def show_login(self):
        self.app.clear_screen()
        frame = ttk.Frame(self.app.container, padding="20")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ttk.Label(frame, text="Вход в систему", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        ttk.Label(frame, text="Логин:").grid(row=1, column=0, sticky="w", pady=5)
        entry_login = ttk.Entry(frame, width=25)
        entry_login.grid(row=1, column=1, pady=5)
        
        ttk.Label(frame, text="Пароль:").grid(row=2, column=0, sticky="w", pady=5)
        entry_pass = ttk.Entry(frame, show="*", width=25)
        entry_pass.grid(row=2, column=1, pady=5)
        
        def handle_login():
            if time.time() < self.lock_until:
                remains = int(self.lock_until - time.time())
                messagebox.showerror("Ошибка", f"Доступ заблокирован. Подождите {remains} сек.")
                return
                
            username = entry_login.get().strip()
            password = entry_pass.get().strip()
            
            conn = sqlite3.connect('food_delivery.db')
            cursor = conn.cursor()
            cursor.execute("""SELECT users.id, username, role_id, roles.name 
                              FROM users JOIN roles ON users.role_id = roles.id WHERE username=?""", (username,))
            user = cursor.fetchone()
            
            if user:
                cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
                if cursor.fetchone():
                    self.failed_attempts = 0
                    self.app.current_user = {"id": user[0], "username": user[1], "role_id": user[2], "role_name": user[3]}
                    conn.close()
                    self.app.show_main_screen()
                    return

            self.failed_attempts += 1
            if self.failed_attempts >= 3:
                self.lock_until = time.time() + 30
                messagebox.showerror("Блокировка", "3 неверные попытки! Вход заблокирован на 30 секунд.")
            else:
                messagebox.showerror("Ошибка", f"Неверный логин или пароль. Попыток осталось: {3 - self.failed_attempts}")
            conn.close()

        ttk.Button(frame, text="Войти", command=handle_login).grid(row=3, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(frame, text="Регистрация", command=self.show_register).grid(row=4, column=0, columnspan=2, pady=5)

    def show_register(self):
        self.app.clear_screen()
        frame = ttk.Frame(self.app.container, padding="20")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ttk.Label(frame, text="Регистрация клиента", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        labels = ["Логин:", "Пароль:", "Повтор пароля:", "Email:", "Телефон:"]
        entries = []
        
        for idx, text in enumerate(labels, start=1):
            ttk.Label(frame, text=text).grid(row=idx, column=0, sticky="w", pady=5)
            is_pass = "*" if "пароль" in text.lower() else ""
            entry = ttk.Entry(frame, show=is_pass, width=25)
            entry.grid(row=idx, column=1, pady=5)
            entries.append(entry)
            
        def handle_register():
            u, p, cp, e, ph = [entry.get().strip() for entry in entries]
            
            if not all([u, p, cp, e, ph]):
                messagebox.showerror("Ошибка", "Заполните все поля!")
                return
            if len(u) < 3:
                messagebox.showerror("Ошибка", "Логин должен быть от 3 символов!")
                return
            if p != cp:
                messagebox.showerror("Ошибка", "Пароли не совпадают!")
                return
            if not validate_password(p):
                messagebox.showerror("Ошибка", "Пароль слишком простой!\nНужна заглавная буква, цифра и спецсимвол (мин. 8 знаков).")
                return
            if not validate_email(e):
                messagebox.showerror("Ошибка", "Неверный Email или домен содержит запрещенный 'admin'!")
                return
                
            conn = sqlite3.connect('food_delivery.db')
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password, email, phone, role_id) VALUES (?, ?, ?, ?, 2)", (u, p, e, ph))
                conn.commit()
                messagebox.showinfo("Успех", "Регистрация успешна!")
                conn.close()
                self.show_login()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Этот логин уже занят!")
                conn.close()

        ttk.Button(frame, text="Создать аккаунт", command=handle_register).grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(frame, text="Назад к входу", command=self.show_login).grid(row=7, column=0, columnspan=2)

# =====================================================================
# БЛОК 4: ВКЛАДКА CRUD ДЛЯ СУЩНОСТИ «МЕНЮ БЛЮД»
# =====================================================================

def build_menu_tab(app, frame):
    search_frame = ttk.Frame(frame, padding=5)
    search_frame.pack(fill="x")
    ttk.Label(search_frame, text="Поиск блюда:").pack(side="left", padx=5)
    entry_search = ttk.Entry(search_frame)
    entry_search.pack(side="left", fill="x", expand=True, padx=5)
    
    columns = ('id', 'name', 'price', 'category')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    tree.heading('id', text='ID')
    tree.heading('name', text='Название блюда')
    tree.heading('price', text='Цена (руб.)')
    tree.heading('category', text='Категория')
    tree.pack(fill="both", expand=True, padx=5, pady=5)
    
    def refresh(search_str=""):
        for row in tree.get_children():
            tree.delete(row)
        conn = sqlite3.connect('food_delivery.db')
        cursor = conn.cursor()
        if search_str:
            cursor.execute("SELECT * FROM menu WHERE name LIKE ?", (f"%{search_str}%",))
        else:
            cursor.execute("SELECT * FROM menu")
        for row in cursor.fetchall():
            tree.insert('', 'end', values=row)
        conn.close()
        
    entry_search.bind("<KeyRelease>", lambda e: refresh(entry_search.get()))
    
    btn_frame = ttk.Frame(frame, padding=5)
    btn_frame.pack(fill="x")
    
    if app.current_user['role_id'] == 1:
        ttk.Button(btn_frame, text="Добавить блюдо", command=lambda: open_form()).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Редактировать", command=lambda: open_form(tree.item(tree.selection())['values'])).pack(side="left", padx=5)
        
        def delete_item():
            selected = tree.selection()
            if not selected: return
            item_id = tree.item(selected)['values'][0]
            if messagebox.askyesno("Подтверждение", f"Вы действительно хотите удалить запись №{item_id}?\nЭто действие нельзя отменить, и все ваши котики умрут от грусти."):
                conn = sqlite3.connect('food_delivery.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM menu WHERE id=?", (item_id,))
                conn.commit()
                conn.close()
                refresh()
        ttk.Button(btn_frame, text="Удалить блюдо", command=delete_item).pack(side="left", padx=5)
    else:
        ttk.Label(btn_frame, text="* Клиенты могут только просматривать меню и искать блюда.", font=("Arial", 9, "italic")).pack(side="left")

    refresh()

    def open_form(item_data=None):
        form = tk.Toplevel(app)
        form.title("Данные блюда")
        form.geometry("300x220")
        
        ttk.Label(form, text="Название (мин 3 симв):").pack(anchor="w", padx=10)
        e_name = ttk.Entry(form)
        e_name.pack(fill="x", padx=10, pady=2)
        
        ttk.Label(form, text="Цена:").pack(anchor="w", padx=10)
        e_price = ttk.Entry(form)
        e_price.pack(fill="x", padx=10, pady=2)
        
        ttk.Label(form, text="Категория (мин 3 симв):").pack(anchor="w", padx=10)
        e_cat = ttk.Entry(form)
        e_cat.pack(fill="x", padx=10, pady=2)
        
        if item_data:
            e_name.insert(0, item_data[1])
            e_price.insert(0, item_data[2])
            e_cat.insert(0, item_data[3])
            
        def save():
            n, p, c = e_name.get().strip(), e_price.get().strip(), e_cat.get().strip()
            if not all([n, p, c]) or len(n) < 3 or len(c) < 3:
                messagebox.showerror("Ошибка", "Заполните все поля! Минимальная длина текста — 3 символа.")
                return
            try:
                p_num = float(p)
            except ValueError:
                messagebox.showerror("Ошибка", "Цена должна быть числом!")
                return
                
            conn = sqlite3.connect('food_delivery.db')
            cursor = conn.cursor()
            if item_data:
                cursor.execute("UPDATE menu SET name=?, price=?, category=? WHERE id=?", (n, p_num, c, item_data[0]))
            else:
                cursor.execute("INSERT INTO menu (name, price, category) VALUES (?, ?, ?)", (n, p_num, c))
            conn.commit()
            conn.close()
            form.destroy()
            refresh()
            
        ttk.Button(form, text="Сохранить", command=save).pack(pady=10)
# =====================================================================
# БЛОК 5: ВКЛАДКА CRUD ДЛЯ СУЩНОСТЕЙ «ЗАКАЗЫ» И «СОДЕРЖИМОЕ»
# =====================================================================

def build_orders_tab(app, frame):
    columns = ('id', 'user', 'address', 'status', 'total')
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    tree.heading('id', text='№ Заказа')
    tree.heading('user', text='Клиент')
    tree.heading('address', text='Адрес доставки')
    tree.heading('status', text='Статус')
    tree.heading('total', text='Итого (руб.)')
    tree.pack(fill="both", expand=True, padx=5, pady=5)
    
    def refresh():
        for row in tree.get_children():
            tree.delete(row)
        conn = sqlite3.connect('food_delivery.db')
        cursor = conn.cursor()
        
        if app.current_user['role_id'] == 1:
            cursor.execute("""SELECT orders.id, users.username, address, status, total_price 
                              FROM orders JOIN users ON orders.user_id = users.id""")
        else:
            cursor.execute("""SELECT orders.id, users.username, address, status, total_price 
                              FROM orders JOIN users ON orders.user_id = users.id WHERE orders.user_id=?""", (app.current_user['id'],))
            
        for row in cursor.fetchall():
            tree.insert('', 'end', values=row)
        conn.close()

    btn_frame = ttk.Frame(frame, padding=5)
    btn_frame.pack(fill="x")
    
    ttk.Button(btn_frame, text="Создать новый заказ", command=lambda: open_order_form()).pack(side="left", padx=5)
    
    if app.current_user['role_id'] == 1:
        ttk.Button(btn_frame, text="Изменить статус", command=lambda: open_order_form(tree.item(tree.selection())['values'])).pack(side="left", padx=5)
        
        def delete_order():
            selected = tree.selection()
            if not selected: return
            order_id = tree.item(selected)['values'][0]
            if messagebox.askyesno("Подтверждение", f"Вы действительно хотите удалить заказ №{order_id}?\nЭто действие нельзя отменить, и все ваши котики умрут от грусти."):
                conn = sqlite3.connect('food_delivery.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM orders WHERE id=?", (order_id,))
                conn.commit()
                conn.close()
                refresh()
        ttk.Button(btn_frame, text="Удалить заказ", command=delete_order).pack(side="left", padx=5)

    refresh()

    def open_order_form(order_data=None):
        form = tk.Toplevel(app)
        form.title("Управление заказом")
        form.geometry("350x260")
        
        if not order_data:
            ttk.Label(form, text="Адрес доставки (мин 3 симв):").pack(anchor="w", padx=10)
            e_address = ttk.Entry(form)
            e_address.pack(fill="x", padx=10, pady=2)
            
            ttk.Label(form, text="Выберите блюдо из меню:").pack(anchor="w", padx=10)
            conn = sqlite3.connect('food_delivery.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, price FROM menu")
            items = cursor.fetchall()
            conn.close()
            
            item_map = {f"{item[1]} ({item[2]}р)": item[0] for item in items}
            cb_item = ttk.Combobox(form, values=list(item_map.keys()), state="readonly")
            cb_item.pack(fill="x", padx=10, pady=2)
            
            ttk.Label(form, text="Количество:").pack(anchor="w", padx=10)
            e_qty = ttk.Entry(form)
            e_qty.pack(fill="x", padx=10, pady=2)
            e_qty.insert(0, "1")
            
            def save_new():
                addr, qty_str = e_address.get().strip(), e_qty.get().strip()
                if not addr or not cb_item.get() or not qty_str:
                    messagebox.showerror("Ошибка", "Заполните все поля!")
                    return
                if len(addr) < 3:
                    messagebox.showerror("Ошибка", "Адрес слишком короткий!")
                    return
                try:
                    qty = int(qty_str)
                    if qty <= 0: raise ValueError
                except ValueError:
                    messagebox.showerror("Ошибка", "Количество должно быть целым положительным числом!")
                    return
                    
                menu_id = item_map[cb_item.get()]
                
                conn = sqlite3.connect('food_delivery.db')
                cursor = conn.cursor()
                cursor.execute("SELECT price FROM menu WHERE id=?", (menu_id,))
                price = cursor.fetchone()[0]
                total = price * qty
                
                cursor.execute("INSERT INTO orders (user_id, address, status, total_price) VALUES (?, ?, 'Принят', ?)",
                               (app.current_user['id'], addr, total))
                order_id = cursor.lastrowid
                
                cursor.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)",
                               (order_id, menu_id, qty))
                conn.commit()
                conn.close()
                form.destroy()
                refresh()
                
            ttk.Button(form, text="Оформить заказ", command=save_new).pack(pady=10)
            
        else:
            ttk.Label(form, text=f"Редактирование заказа №{order_data[0]}", font=("Arial", 10, "bold")).pack(pady=5)
            ttk.Label(form, text="Статус заказа:").pack(anchor="w", padx=10)
            cb_status = ttk.Combobox(form, values=["Принят", "Готовится", "В пути", "Доставлен"], state="readonly")
            cb_status.pack(fill="x", padx=10, pady=5)
            cb_status.set(order_data[3])
            
            def update_status():
                conn = sqlite3.connect('food_delivery.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET status=? WHERE id=?", (cb_status.get(), order_data[0]))
                conn.commit()
                conn.close()
                form.destroy()
                refresh()
                
            ttk.Button(form, text="Обновить статус", command=update_status).pack(pady=10)

# =====================================================================
# БЛОК 6: ГЛАВНЫЙ ЭКРАН И ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
# =====================================================================

class DeliveryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Служба доставки еды «Вкусный Код»")
        self.geometry("900x600")
        
        self.current_user = None
        
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        
        self.auth_manager = AuthScreens(self)
        self.auth_manager.show_login()

    def clear_screen(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_main_screen(self):
        self.clear_screen()
        
        top_bar = ttk.Frame(self.container, padding="10", relief="raised")
        top_bar.pack(fill="x", side="top")
        
        welcome = f"Рады видеть вас, {self.current_user['username']}! Роль в системе: [{self.current_user['role_name']}]"
        ttk.Label(top_bar, text=welcome, font=("Arial", 11, "bold")).pack(side="left")
        
        def logout():
            if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
                self.current_user = None
                self.auth_manager.show_login()
                
        ttk.Button(top_bar, text="Выйти", command=logout).pack(side="right")
        
        notebook = ttk.Notebook(self.container)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Вкладка 1: Главная статистика
        tab_home = ttk.Frame(notebook)
        notebook.add(tab_home, text=" Сводная информация ")
        self.build_stats_tab(tab_home)
        
        # Вкладка 2: Блюда
        tab_menu = ttk.Frame(notebook)
        notebook.add(tab_menu, text=" Меню блюд ")
        build_menu_tab(self, tab_menu)
        
        # Вкладка 3: Заказы
        tab_orders = ttk.Frame(notebook)
        notebook.add(tab_orders, text=" Заказы ")
        build_orders_tab(self, tab_orders)

    def build_stats_tab(self, frame):
        conn = sqlite3.connect('food_delivery.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM menu")
        count_menu = cursor.fetchone()[0]
        
        if self.current_user['role_id'] == 1:
            cursor.execute("SELECT COUNT(*) FROM orders")
            count_orders = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE role_id=2")
            count_users = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (self.current_user['id'],))
            count_orders = cursor.fetchone()[0]
            count_users = 1

        lbl_frame = ttk.LabelFrame(frame, text=" Сводная статистика ", padding=20)
        lbl_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(lbl_frame, text=f"Всего доступных блюд в каталоге: {count_menu}", font=("Arial", 12)).pack(anchor="w", pady=5)
        ttk.Label(lbl_frame, text=f"Всего ваших/системных заказов: {count_orders}", font=("Arial", 12)).pack(anchor="w", pady=5)
        if self.current_user['role_id'] == 1:
            ttk.Label(lbl_frame, text=f"Зарегистрированных клиентов в БД: {count_users}", font=("Arial", 12)).pack(anchor="w", pady=5)
            
        ttk.Label(lbl_frame, text="\nПоследние новинки меню кухни:", font=("Arial", 10, "bold")).pack(anchor="w")
        cursor.execute("SELECT name, price FROM menu ORDER BY id DESC LIMIT 3")
        for name, price in cursor.fetchall():
            ttk.Label(lbl_frame, text=f" • {name} — {price} руб.").pack(anchor="w", padx=10)
            
        conn.close()

if __name__ == "__main__":
    init_db()
    print("БАЗА И ОКНО СТАРТУЮТ...")
    app = DeliveryApp()
    app.mainloop()


