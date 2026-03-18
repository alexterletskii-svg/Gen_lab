import sqlite3

conn = sqlite3.connect('game_diagnostics.db')
cursor = conn.cursor()

# Создание таблицы players (без изменений)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_time REAL,          -- Общее время прохождения уровня
        total_score INTEGER,      -- Общий счёт игрока
        level_reached INTEGER,    -- Достигнутый уровень
        avg_reaction_time REAL,   -- Среднее время реакции на уровне
        total_errors INTEGER,     -- Общее количество ошибок (попыток пройти через стену)
        state_self_assessment TEXT, -- Самооценка состояния из первого вопроса
        age INTEGER,              -- Возраст игрока (полных лет)
        total_game_time REAL      -- Общее время игры (от начала до завершения)
    )
''')

# Создание таблицы questions (без изменений)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL
    )
''')

# Создание таблицы answers (без изменений)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        question_id INTEGER,
        answer_text TEXT NOT NULL,
        FOREIGN KEY (player_id) REFERENCES players(id),
        FOREIGN KEY (question_id) REFERENCES questions(question_id)
    )
''')

# Создание таблицы level_stats (без изменений)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS level_stats (
        stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        level INTEGER,
        completion_time REAL,    -- Время прохождения уровня
        score INTEGER,           -- Очки за уровень
        reaction_time_avg REAL,  -- Среднее время реакции на уровне
        errors_count INTEGER,    -- Количество ошибок на уровне
        pause_duration REAL,     -- Время паузы перед продолжением на следующий уровень
        FOREIGN KEY (player_id) REFERENCES players(id)
    )
''')

# Создание таблицы answer_options для хранения вариантов ответа
cursor.execute('''
    CREATE TABLE IF NOT EXISTS answer_options (
        option_id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        option_text TEXT NOT NULL,
        FOREIGN KEY (question_id) REFERENCES questions(question_id)
    )
''')

# Вставка начальных вопросов
questions_list = [
    ("Как вы оцениваете своё настроение сейчас?",),
    ("Чувствуете ли вы стресс?",),
    ("Как вы оцениваете свой уровень энергии?",),
    ("Вы выспались сегодня?",),
    ("Были ли у вас сегодня конфликтные ситуации?",)
]

cursor.executemany('INSERT OR IGNORE INTO questions (question_text) VALUES (?)', questions_list)

# Добавление начальных вариантов ответа для вопросов
options_list = [
    (1, "Отлично"), (1, "Хорошо"), (1, "Нормально"), (1, "Плохо"),
    (2, "Да, сильно"), (2, "Немного"), (2, "Нет"),
    (3, "Высокий"), (3, "Средний"), (3, "Низкий"),
    (4, "Да, полностью"), (4, "Не совсем"), (4, "Нет"),
    (5, "Да, были"), (5, "Нет")
]

cursor.executemany('INSERT OR IGNORE INTO answer_options (question_id, option_text) VALUES (?, ?)', options_list)

conn.commit()
conn.close()

print("База данных 'game_diagnostics.db' успешно создана с необходимыми таблицами и начальными данными.")
