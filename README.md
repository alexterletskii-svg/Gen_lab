# Генератор лабиринтов и Аналитическая платформа (Game Diagnostics)

Комплексный программный комплекс, состоящий из десктопной игры-лабиринта и веб-дашборда для анализа когнитивных и поведенческих показателей игроков. Проект собирает данные во время игрового процесса (время реакции, количество ошибок, время прохождения) и предоставляет удобный веб-интерфейс для их визуализации, сравнения и экспорта.

## Архитектура проекта

Проект логически разделен на три основных компонента:
1. **Модуль сбора данных (Игровой клиент - `Gen_lab.py`)** — написан на Python с использованием библиотеки `pygame`. Отвечает за генерацию уровней, взаимодействие с пользователем и фиксацию метрик в реальном времени.
2. **Модуль анализа данных (Веб-платформа - `analis.py`)** — написан на Python с использованием фреймворка `Flask`. Предоставляет аналитические дашборды, профили игроков и инструменты экспорта.
3. **База данных (`create_bd.py`)** — скрипт инициализации реляционной базы данных SQLite (`game_diagnostics.db`).

---

## Подробное описание функций и логики работы

### 1. Модуль сбора данных (Игровой клиент)

Этот модуль отвечает за "полевую" работу: регистрацию пользователя, проведение опроса и трекинг его действий в лабиринте.

#### Процедурная генерация лабиринта (`Класс Maze`)
Генерация лабиринта реализована на основе алгоритма поиска в глубину (Depth-First Search) с возвратом (backtracking). Это гарантирует создание "идеального" лабиринта, в котором существует ровно один путь между любыми двумя точками без циклов.

```python
class Maze:
    def __init__(self, cols, rows, complexity):
        self.cols = cols
        self.rows = rows
        self.grid = [[1 for _ in range(cols)] for _ in range(rows)]
        self.complexity = complexity
        self.generate_maze()

    def generate_maze(self):
        stack = []
        current_cell = (0, 0)
        self.grid[0][0] = 0 # 0 - проход, 1 - стена
        stack.append(current_cell)

        while stack:
            neighbors = self.get_neighbors(current_cell)
            if neighbors:
                neighbor = random.choice(neighbors)
                self.remove_wall(current_cell, neighbor)
                self.grid[neighbor[1]][neighbor[0]] = 0
                stack.append(neighbor)
                current_cell = neighbor
            else:
                current_cell = stack.pop()
```

#### Сбор первичных данных и анкетирование (`handle_questionnaire`)
Перед началом сессии система собирает базовые демографические данные (имя, возраст) и проводит опрос для оценки текущего состояния игрока. Вопросы и варианты ответов динамически загружаются из БД.

```python
# Извлечение вопросов из базы данных перед игрой
db_cursor.execute('SELECT question_id, question_text FROM questions')
questions = db_cursor.fetchall()
question_options = {}

for question in questions:
    question_id = question[0]
    db_cursor.execute('SELECT option_text FROM answer_options WHERE question_id = ?', (question_id,))
    options = [row[0] for row in db_cursor.fetchall()]
    question_options[question_id] = options if options else ["Да", "Нет"]
```

#### Трекинг игровых метрик (`handle_game`)
В основном игровом цикле происходит непрерывный сбор данных:
*   **Время реакции:** Вычисляется как разница во времени (`time.time()`) между последовательными нажатиями клавиш управления.
*   **Ошибки:** Каждая попытка игрока сдвинуться в ячейку со значением `1` (стена) фиксируется как ошибка, сопровождаясь визуальным откликом.
*   **Время прохождения:** Разница между временем старта уровня и моментом достижения финишной ячейки.

```python
# Логика фиксации времени реакции
current_time = time.time()
if last_move_time > 0:
    reaction_time = current_time - last_move_time
    reaction_times.append(reaction_time)
last_move_time = current_time

# Логика фиксации ошибок
if is_wall(next_x, next_y):
    errors_count += 1
    trigger_visual_error_feedback()
```

### 2. Модуль анализа данных (Веб-платформа)

Веб-приложение на Flask читает собранные данные, агрегирует их и предоставляет интерфейс для исследователя/аналитика.

#### Подключение и маршрутизация
Используется `sqlite3.Row` для представления строк базы данных в виде словарей, что упрощает передачу данных в Jinja2 шаблоны.

```python
def get_db_connection():
    conn = sqlite3.connect('game_diagnostics.db')
    conn.row_factory = sqlite3.Row
    return conn
```

#### Анализ индивидуального профиля (`/player/<name>`)
Функция `player_analysis` выполняет комплексные SQL-запросы для формирования полного отчета по игроку, объединяя данные из таблиц `players`, `level_stats` и `answers`.

```python
@app.route('/player/<name>')
def player_analysis(name):
    conn = get_db_connection()
    
    # Агрегированная статистика игрока
    player_data = conn.execute('''
        SELECT age, total_game_time, level_reached, total_score, avg_reaction_time, total_errors
        FROM players WHERE name = ?
    ''', (name,)).fetchone()
    
    # Поуровневая детализация
    level_data = conn.execute('''
        SELECT level, completion_time, score, reaction_time_avg, errors_count
        FROM level_stats
        WHERE player_id = (SELECT id FROM players WHERE name = ?)
        ORDER BY level
    ''', (name,)).fetchall()
    
    conn.close()
    return render_template('player_analysis.html', player=player_data, levels=level_data)
```

#### Сравнение игроков и Дашборды (`/compare`, `/dashboard`)
Приложение позволяет выбрать нескольких игроков для параллельного сравнения. Данные передаются на фронтенд, где с помощью библиотек (например, Chart.js) строятся графики распределения времени реакции и количества ошибок.

#### Экспорт данных (`/export`)
Для внешнего анализа (в Excel, SPSS или Python) реализована выгрузка данных в CSV с использованием библиотеки `pandas`.

```python
import pandas as pd
import io
from flask import send_file

@app.route('/export_player/<name>')
def export_player(name):
    # ... получение данных из БД ...
    df = pd.DataFrame(data, columns=['Уровень', 'Время', 'Очки', 'Реакция', 'Ошибки'])
    output = io.BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=f'{name}_report.csv')
```

---

## Структура базы данных (SQLite)

База данных нормализована для эффективного хранения метрик и результатов анкетирования. Ниже представлены структуры основных таблиц.

### 1. Таблица `players` (Данные игроков)
Хранит общую информацию о профиле игрока и его суммарные достижения за сессию.

| Имя столбца | Тип данных | Описание |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Первичный ключ (AUTOINCREMENT) |
| `name` | `TEXT` | Имя игрока (NOT NULL) |
| `game_date` | `TIMESTAMP` | Дата и время проведения игры (DEFAULT CURRENT_TIMESTAMP) |
| `total_time` | `REAL` | Общее время прохождения всех уровней (в секундах) |
| `total_score` | `INTEGER` | Общий счет, набранный за игру |
| `level_reached` | `INTEGER` | Максимальный уровень, до которого дошел игрок |
| `avg_reaction_time` | `REAL` | Среднее время реакции за всю игру (в секундах) |
| `total_errors` | `INTEGER` | Суммарное количество ошибок (столкновений со стенами) |
| `state_self_assessment`| `TEXT` | Самооценка состояния (ответ на базовый вопрос анкеты) |
| `age` | `INTEGER` | Возраст игрока |
| `total_game_time` | `REAL` | Общее время нахождения в приложении (от старта до выхода) |

```sql
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_time REAL,
    total_score INTEGER,
    level_reached INTEGER,
    avg_reaction_time REAL,
    total_errors INTEGER,
    state_self_assessment TEXT,
    age INTEGER,
    total_game_time REAL
);
```

### 2. Таблица `level_stats` (Статистика по уровням)
Хранит детализированную статистику прохождения каждого конкретного уровня для каждого игрока.

| Имя столбца | Тип данных | Описание |
| :--- | :--- | :--- |
| `stat_id` | `INTEGER` | Первичный ключ (AUTOINCREMENT) |
| `player_id` | `INTEGER` | Внешний ключ (ссылается на `players.id`) |
| `level` | `INTEGER` | Порядковый номер уровня |
| `completion_time` | `REAL` | Время, затраченное на прохождение уровня (в секундах) |
| `score` | `INTEGER` | Очки, полученные конкретно за этот уровень |
| `reaction_time_avg` | `REAL` | Среднее время реакции на данном уровне |
| `errors_count` | `INTEGER` | Количество ошибок, совершенных на уровне |
| `pause_duration` | `REAL` | Суммарное время, проведенное в меню паузы (в секундах) |

```sql
CREATE TABLE IF NOT EXISTS level_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER,
    level INTEGER,
    completion_time REAL,
    score INTEGER,
    reaction_time_avg REAL,
    errors_count INTEGER,
    pause_duration REAL,
    FOREIGN KEY (player_id) REFERENCES players (id)
);
```

### 3. Таблицы анкетирования (`questions`, `answer_options`, `answers`)
Система вопросов и ответов нормализована для возможности гибкого редактирования опросников через веб-интерфейс.

**Таблица `questions`** (Справочник вопросов)
| Имя столбца | Тип данных | Описание |
| :--- | :--- | :--- |
| `question_id` | `INTEGER` | Первичный ключ (AUTOINCREMENT) |
| `question_text` | `TEXT` | Текст вопроса (NOT NULL) |

**Таблица `answer_options`** (Варианты ответов)
| Имя столбца | Тип данных | Описание |
| :--- | :--- | :--- |
| `option_id` | `INTEGER` | Первичный ключ (AUTOINCREMENT) |
| `question_id` | `INTEGER` | Внешний ключ (ссылается на `questions.question_id`) |
| `option_text` | `TEXT` | Текст варианта ответа (NOT NULL) |

**Таблица `answers`** (Ответы пользователей)
| Имя столбца | Тип данных | Описание |
| :--- | :--- | :--- |
| `answer_id` | `INTEGER` | Первичный ключ (AUTOINCREMENT) |
| `player_id` | `INTEGER` | Внешний ключ (ссылается на `players.id`) |
| `question_id` | `INTEGER` | Внешний ключ (ссылается на `questions.question_id`) |
| `answer_text` | `TEXT` | Выбранный текст ответа (NOT NULL) |

```sql
CREATE TABLE IF NOT EXISTS questions (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS answer_options (
    option_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    option_text TEXT NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions (question_id)
);

CREATE TABLE IF NOT EXISTS answers (
    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER,
    question_id INTEGER,
    answer_text TEXT NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players (id),
    FOREIGN KEY (question_id) REFERENCES questions (question_id)
);
```

---

## Инструкция по развертыванию

1. Клонируйте репозиторий на локальную машину:
```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

2. Создайте и активируйте виртуальное окружение (рекомендуется):
```bash
python -m venv venv
# Для Windows:
venv\Scripts\activate
# Для Linux/MacOS:
source venv/bin/activate
```

3. Установите необходимые зависимости:
```bash
pip install pygame flask pandas webview
```

4. Инициализируйте базу данных (создаст файл `game_diagnostics.db`):
```bash
python create_bd.py
```

5. Для начала сбора данных запустите игровой клиент:
```bash
python Gen_lab.py
```

6. Для просмотра аналитики запустите веб-сервер:
```bash
python analis.py
```

7. Архив программы для запуска под Windows:
```bash
https://disk.yandex.ru/d/3zBncRJBfjxqKA
```
