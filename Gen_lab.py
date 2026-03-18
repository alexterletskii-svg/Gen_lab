import pygame
import random
import sqlite3
import time
import math
from datetime import datetime

# Инициализация Pygame
pygame.init()

# Константы для окна и шрифтов
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Генератор лабиринтов")

font_large = pygame.font.SysFont('Arial', 36)
font_small = pygame.font.SysFont('Arial', 24)
font_tiny = pygame.font.SysFont('Arial', 18)

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
DARK_RED = (139, 0, 0)

# Подключение к базе данных с обработкой ошибок
try:
    conn = sqlite3.connect('game_diagnostics.db')
    db_cursor = conn.cursor()
except sqlite3.Error as e:
    print(f"Ошибка подключения к базе данных: {e}")
    exit(1)

# Получение вопросов и вариантов ответов из базы данных
try:
    db_cursor.execute('SELECT question_id, question_text FROM questions')
    questions = db_cursor.fetchall()
    question_options = {}
    for question in questions:
        question_id = question[0]
        db_cursor.execute('SELECT option_text FROM answer_options WHERE question_id = ?', (question_id,))
        options = [row[0] for row in db_cursor.fetchall()]
        question_options[question_id] = options if options else ["Да", "Нет"]
except sqlite3.Error as e:
    print(f"Ошибка получения данных из базы: {e}")
    questions = []
    question_options = {}


def wrap_text(text, font, max_width):
    """Разбивает текст на строки так, чтобы каждая помещалась в max_width."""
    words = text.split()
    lines, current = [], ''
    for w in words:
        test = f'{current} {w}'.strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


class Maze:
    """Класс для генерации и управления лабиринтом."""

    def __init__(self, cols, rows, complexity):
        self.cols = cols
        self.rows = rows
        self.grid = [[1 for _ in range(cols)] for _ in range(rows)]
        self.complexity = complexity
        self.generate_maze()

    def generate_maze(self):
        stack = []
        current_cell = (0, 0)
        self.grid[0][0] = 0
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

    def get_neighbors(self, cell):
        neighbors = []
        directions = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        for dx, dy in directions:
            nx, ny = cell[0] + dx, cell[1] + dy
            if 0 <= nx < self.cols and 0 <= ny < self.rows and self.grid[ny][nx] == 1:
                neighbors.append((nx, ny))
        return neighbors

    def remove_wall(self, current_cell, neighbor):
        x = (current_cell[0] + neighbor[0]) // 2
        y = (current_cell[1] + neighbor[1]) // 2
        self.grid[y][x] = 0


def draw_button(screen, rect, text, font, fg_color, bg_color):
    """Отрисовка кнопки с текстом."""
    pygame.draw.rect(screen, bg_color, rect)
    button_text = font.render(text, True, fg_color)
    button_text_rect = button_text.get_rect(center=rect.center)
    screen.blit(button_text, button_text_rect)
    return rect


def draw_input_box(screen, prompt, input_text, font, width, height):
    """Отрисовка поля ввода с мигающим курсором."""
    prompt_text = font.render(prompt, True, WHITE)
    input_text_render = font.render(input_text, True, WHITE)
    cursor_time = time.time() % 1
    input_cursor = "|" if cursor_time < 0.5 else ""
    cursor_text = font.render(input_cursor, True, WHITE)

    screen.blit(prompt_text, (width // 2 - prompt_text.get_width() // 2, height // 2 - 50))
    input_box = pygame.Rect(width // 2 - 150, height // 2 - 15, 300, 30)
    pygame.draw.rect(screen, WHITE, input_box, 2)
    text_pos = (input_box.x + 5, input_box.y + (input_box.height - input_text_render.get_height()) // 2)
    screen.blit(input_text_render, text_pos)
    cursor_pos = (text_pos[0] + input_text_render.get_width(), text_pos[1])
    screen.blit(cursor_text, cursor_pos)
    return input_box


def draw_preloader(screen, angle, center_x, center_y, radius=50, dot_radius=10, num_dots=8):
    """Отрисовка анимации прелоадера."""
    for i in range(num_dots):
        dot_angle = angle + (i * (2 * math.pi / num_dots))
        x = center_x + radius * math.cos(dot_angle)
        y = center_y + radius * math.sin(dot_angle)
        pygame.draw.circle(screen, WHITE, (int(x), int(y)), dot_radius)


def handle_start_screen(events, width, height):
    """Обработка событий и отрисовка стартового экрана."""
    screen.fill(BLACK)
    title_text = font_large.render("Добро пожаловать в Генератор лабиринтов!", True, WHITE)
    start_text = font_small.render("Нажмите 'Начать', чтобы продолжить.", True, WHITE)
    start_button = draw_button(screen, pygame.Rect(width // 2 - 100, height // 2, 200, 50), "Начать", font_small, BLACK,
                               WHITE)
    score_list_button = draw_button(screen, pygame.Rect(width // 2 - 100, height // 2 + 60, 200, 50), "Список очков",
                                    font_small, BLACK, WHITE)
    screen.blit(title_text, (width // 2 - title_text.get_width() // 2, height // 2 - 100))
    screen.blit(start_text, (width // 2 - start_text.get_width() // 2, height // 2 - 50))

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if start_button.collidepoint(event.pos):
                return "enter_name"
            elif score_list_button.collidepoint(event.pos):
                return "score_screen"
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return None
    return "start_screen"


def handle_enter_name(events, user_name, width, height):
    """Обработка ввода имени пользователя."""
    screen.fill(BLACK)
    draw_input_box(screen, "Введите ваше имя:", user_name, font_small, width, height)
    new_state = "enter_name"
    new_name = user_name

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and user_name != "":
                new_state = "enter_age"
            elif event.key == pygame.K_BACKSPACE:
                new_name = user_name[:-1]
            elif event.key == pygame.K_ESCAPE:
                new_state = "start_screen"
                new_name = ""
            else:
                new_name += event.unicode
    return new_state, new_name


def handle_enter_age(events, user_age, width, height):
    """Обработка ввода возраста пользователя."""
    screen.fill(BLACK)
    draw_input_box(screen, "Введите ваш возраст (полных лет):", user_age, font_small, width, height)
    new_state = "enter_age"
    new_age = user_age

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and user_age != "":
                try:
                    age_int = int(user_age)
                    if 0 < age_int < 150:
                        new_state = "questionnaire"
                    else:
                        new_age = ""
                except ValueError:
                    new_age = ""
            elif event.key == pygame.K_BACKSPACE:
                new_age = user_age[:-1]
            elif event.unicode.isdigit():
                new_age += event.unicode
            elif event.key == pygame.K_ESCAPE:
                new_state = "enter_name"
                new_age = ""
    return new_state, new_age


def handle_questionnaire(events, current_question_index, answers, user_name, user_age, width, height):
    """Обработка анкеты с вопросами."""
    screen.fill(BLACK)
    question_id, question_raw = questions[current_question_index]
    wrapped_lines = wrap_text(question_raw, font_small, width - 100)
    y = height // 2 - 100
    for line in wrapped_lines:
        q_line = font_small.render(line, True, WHITE)
        screen.blit(q_line, (width // 2 - q_line.get_width() // 2, y))
        y += font_small.get_height() + 5
    y += 20

    options = question_options[question_id]
    button_height = 50
    buttons = []
    for i, option in enumerate(options):
        button = pygame.Rect(width // 2 - 100, y + i * button_height, 200, button_height - 10)
        draw_button(screen, button, option, font_small, BLACK, WHITE)
        buttons.append((button, option))

    new_state = "questionnaire"
    new_index = current_question_index
    new_answers = answers[:]
    player_id = None

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            for button, option in buttons:
                if button.collidepoint(event.pos):
                    new_answers.append((question_id, option))
                    if current_question_index < len(questions) - 1:
                        new_index += 1
                    else:
                        try:
                            db_cursor.execute(
                                'INSERT INTO players (name, state_self_assessment, age) VALUES (?, ?, ?)',
                                (user_name, new_answers[0][1], int(user_age)))
                            conn.commit()
                            player_id = db_cursor.lastrowid
                            for q_id, answer in new_answers:
                                db_cursor.execute(
                                    'INSERT INTO answers (player_id, question_id, answer_text) VALUES (?, ?, ?)',
                                    (player_id, q_id, answer))
                            conn.commit()
                        except sqlite3.Error as e:
                            print(f"Ошибка сохранения данных в базу: {e}")
                        new_state = "loading_screen"
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                new_state = "enter_age"
                new_answers = []
                new_index = 0
    return new_state, new_index, new_answers, player_id


def handle_game(events, maze, player_pos, start_time, last_key_time, reaction_times, errors, level, error_flash_time):
    """Обработка игрового процесса с миганием экрана при ошибке."""
    current_time = time.time()
    # Определяем, нужно ли мигать экраном красным (если была ошибка недавно)
    flash_duration = 0.3  # Длительность мигания экрана в секундах
    background_color = DARK_RED if error_flash_time and (current_time - error_flash_time) < flash_duration else BLACK
    screen.fill(background_color)

    elapsed_time = time.time() - start_time
    cell_size = min(WIDTH / maze.cols, HEIGHT / maze.rows)
    offset_x = (WIDTH - maze.cols * cell_size) / 2
    offset_y = (HEIGHT - maze.rows * cell_size) / 2

    for y in range(maze.rows):
        for x in range(maze.cols):
            rect = pygame.Rect(int(offset_x + x * cell_size), int(offset_y + y * cell_size),
                               int(cell_size), int(cell_size))
            if maze.grid[y][x] == 1:
                pygame.draw.rect(screen, WHITE, rect)

    start_rect = pygame.Rect(int(offset_x), int(offset_y), int(cell_size), int(cell_size))
    pygame.draw.rect(screen, BLUE, start_rect)
    exit_rect = pygame.Rect(int(offset_x + (maze.cols - 1) * cell_size),
                            int(offset_y + (maze.rows - 1) * cell_size), int(cell_size), int(cell_size))
    pygame.draw.rect(screen, GREEN, exit_rect)

    player_color = RED if errors > 0 and time.time() % 0.5 < 0.25 else (255, 0, 0)
    player_rect = pygame.Rect(int(offset_x + player_pos[0] * cell_size),
                              int(offset_y + player_pos[1] * cell_size), int(cell_size), int(cell_size))
    pygame.draw.rect(screen, player_color, player_rect)

    level_text = font_small.render(f"Уровень: {level}", True, WHITE)
    time_text = font_small.render(f"Время: {int(elapsed_time)} сек", True, WHITE)
    screen.blit(level_text, (10, 10))
    screen.blit(time_text, (10, 40))

    new_state = "game"
    new_pos = player_pos[:]
    new_times = reaction_times[:]
    new_errors = errors
    new_last_key_time = last_key_time
    new_error_flash_time = error_flash_time

    for event in events:
        if event.type == pygame.KEYDOWN:
            current_time = time.time()
            reaction_time = current_time - last_key_time
            new_times.append(reaction_time)
            new_last_key_time = current_time
            dx, dy = 0, 0
            if event.key == pygame.K_LEFT:
                dx = -1
            elif event.key == pygame.K_RIGHT:
                dx = 1
            elif event.key == pygame.K_UP:
                dy = -1
            elif event.key == pygame.K_DOWN:
                dy = 1
            new_x = player_pos[0] + dx
            new_y = player_pos[1] + dy
            if 0 <= new_x < maze.cols and 0 <= new_y < maze.rows:
                if maze.grid[new_y][new_x] == 0:
                    new_pos = [new_x, new_y]
                else:
                    new_errors += 1
                    new_error_flash_time = current_time  # Запускаем мигание экрана при ошибке
            elif event.key == pygame.K_ESCAPE:
                new_state = "start_screen"

    return new_state, new_pos, new_times, new_errors, new_last_key_time, new_error_flash_time


def main():
    """Основная функция игры."""
    global screen, WIDTH, HEIGHT
    clock = pygame.time.Clock()
    running = True
    game_state = "start_screen"
    user_name = ""
    user_age = ""
    maze = None
    player_pos = [0, 0]
    cell_size = 20
    level = 1
    score = 0
    start_time = 0
    game_start_time = 0
    elapsed_time = 0
    total_game_time = 0
    last_key_time = time.time()
    reaction_times = []
    errors = 0
    player_id = None
    current_question_index = 0
    answers = []
    pause_start_time = 0
    pause_duration = 0
    waiting_for_continue = False
    loading_start = 0
    message_change_time = 0
    current_message = ""
    preloader_radius = 50
    preloader_dot_radius = 10
    preloader_num_dots = 8
    preloader_speed = 0.05
    preloader_center_x = WIDTH // 2
    preloader_center_y = HEIGHT // 2
    preloader_angle = 0
    error_flash_time = 0  # Время начала мигания экрана при ошибке

    messages = [
        "Генерируем лабиринты....", "Подсчитываем варианты.....", "Подключаем алгоритмы....",
        "Перемешиваем проходы....", "Создаем тайные тропинки....", "Мозговой штурм в процессе...",
        "Запутываем тропинки...", "Ищем выход из сложных ситуаций...", "Ловим миньонов для помощи...",
        "Заполняем пустые комнаты загадками...", "Настраиваем вашу карту приключений...",
        "Перемешиваем стены и проходы...", "Прячем выход по лучше...", "Плетем паутину загадок...",
        "Загружаем карту неизвестного...", "Плетем нити судьбы...", "Открываем двери в неизведанное...",
        "Приоткрываем тайны прошлого...", "Настраиваем загадочные механизмы..."
    ]

    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
                if player_id and game_start_time:
                    total_game_time = time.time() - game_start_time
                    try:
                        db_cursor.execute('UPDATE players SET total_game_time = ? WHERE id = ?',
                                          (total_game_time, player_id))
                        conn.commit()
                    except sqlite3.Error as e:
                        print(f"Ошибка обновления данных: {e}")
            elif event.type == pygame.VIDEORESIZE:
                WIDTH, HEIGHT = event.w, event.h
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                if maze:
                    cell_size = min(WIDTH / maze.cols, HEIGHT / maze.rows)
                preloader_center_x = WIDTH // 2
                preloader_center_y = HEIGHT // 2

        preloader_angle += preloader_speed

        if game_state == "start_screen":
            game_state = handle_start_screen(events, WIDTH, HEIGHT)
            if game_state is None:
                running = False

        elif game_state == "enter_name":
            game_state, user_name = handle_enter_name(events, user_name, WIDTH, HEIGHT)

        elif game_state == "enter_age":
            game_state, user_age = handle_enter_age(events, user_age, WIDTH, HEIGHT)
            if game_state == "questionnaire":
                current_question_index = 0
                answers = []

        elif game_state == "questionnaire":
            game_state, current_question_index, answers, player_id = handle_questionnaire(
                events, current_question_index, answers, user_name, user_age, WIDTH, HEIGHT
            )
            if game_state == "loading_screen":
                loading_start = time.time()
                message_change_time = time.time()
                current_message = random.choice(messages)
                game_start_time = time.time()

        elif game_state == "loading_screen":
            screen.fill(BLACK)
            draw_preloader(screen, preloader_angle, preloader_center_x, preloader_center_y,
                           preloader_radius, preloader_dot_radius, preloader_num_dots)
            current_time = time.time()
            if current_time - message_change_time > 1.5:
                current_message = random.choice(messages)
                message_change_time = current_time
            message_text = font_large.render(current_message, True, WHITE)
            screen.blit(message_text, (WIDTH // 2 - message_text.get_width() // 2,
                                       HEIGHT // 2 + preloader_radius + 30))
            if current_time - loading_start > random.randint(5, 7):
                game_state = "game"
                cols = rows = level * 2 + 5
                maze = Maze(cols, rows, level)
                player_pos = [0, 0]
                cell_size = min(WIDTH / cols, HEIGHT / rows)
                start_time = time.time()
                last_key_time = time.time()
                reaction_times = []
                errors = 0
                error_flash_time = 0  # Сбрасываем время мигания при новом уровне

        elif game_state == "game":
            game_state, player_pos, reaction_times, errors, last_key_time, error_flash_time = handle_game(
                events, maze, player_pos, start_time, last_key_time, reaction_times, errors, level, error_flash_time
            )
            if player_pos == [maze.cols - 1, maze.rows - 1]:
                elapsed_time = time.time() - start_time
                level_score = int(1000 / (elapsed_time + 1) * level)
                score += level_score
                avg_reaction_time = sum(reaction_times) / len(reaction_times) if reaction_times else 0
                try:
                    db_cursor.execute(
                        'INSERT INTO level_stats (player_id, level, completion_time, score, reaction_time_avg, errors_count) VALUES (?, ?, ?, ?, ?, ?)',
                        (player_id, level, elapsed_time, level_score, avg_reaction_time, errors))
                    db_cursor.execute(
                        'UPDATE players SET total_time = ?, total_score = ?, level_reached = ?, avg_reaction_time = ?, total_errors = ? WHERE id = ?',
                        (elapsed_time, score, level, avg_reaction_time, errors, player_id))
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"Ошибка сохранения статистики: {e}")
                game_state = "continue_prompt"
                pause_start_time = time.time()
                waiting_for_continue = True
                level += 1
            elif game_state == "start_screen":
                total_game_time = time.time() - game_start_time
                try:
                    db_cursor.execute('UPDATE players SET total_game_time = ? WHERE id = ?',
                                      (total_game_time, player_id))
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"Ошибка обновления времени игры: {e}")
                maze = None
                player_id = None

        elif game_state == "continue_prompt":
            screen.fill(BLACK)
            report_title = font_large.render("Уровень пройден!", True, WHITE)
            continue_text = font_small.render("Хотите продолжить?", True, WHITE)
            hint_text = font_tiny.render("Enter - Продолжить, Esc - Завершить", True, WHITE)
            continue_button = draw_button(screen, pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 50, 200, 50),
                                          "Продолжить", font_small, BLACK, WHITE)
            end_button = draw_button(screen, pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 110, 200, 50),
                                     "Завершить", font_small, BLACK, WHITE)
            screen.blit(report_title, (WIDTH // 2 - report_title.get_width() // 2, HEIGHT // 2 - 50))
            screen.blit(continue_text, (WIDTH // 2 - continue_text.get_width() // 2, HEIGHT // 2))
            screen.blit(hint_text, (WIDTH // 2 - hint_text.get_width() // 2, HEIGHT // 2 + 170))

            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if continue_button.collidepoint(event.pos):
                        pause_duration = time.time() - pause_start_time
                        try:
                            db_cursor.execute(
                                'UPDATE level_stats SET pause_duration = ? WHERE player_id = ? AND level = ?',
                                (pause_duration, player_id, level - 1))
                            conn.commit()
                        except sqlite3.Error as e:
                            print(f"Ошибка обновления времени паузы: {e}")
                        game_state = "loading_screen"
                        loading_start = time.time()
                        message_change_time = time.time()
                        current_message = random.choice(messages)
                        waiting_for_continue = False
                    elif end_button.collidepoint(event.pos):
                        total_game_time = time.time() - game_start_time
                        try:
                            db_cursor.execute('UPDATE players SET total_game_time = ? WHERE id = ?',
                                              (total_game_time, player_id))
                            conn.commit()
                        except sqlite3.Error as e:
                            print(f"Ошибка обновления времени игры: {e}")
                        game_state = "start_screen"
                        maze = None
                        player_id = None
                        waiting_for_continue = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        pause_duration = time.time() - pause_start_time
                        try:
                            db_cursor.execute(
                                'UPDATE level_stats SET pause_duration = ? WHERE player_id = ? AND level = ?',
                                (pause_duration, player_id, level - 1))
                            conn.commit()
                        except sqlite3.Error as e:
                            print(f"Ошибка обновления времени паузы: {e}")
                        game_state = "loading_screen"
                        loading_start = time.time()
                        message_change_time = time.time()
                        current_message = random.choice(messages)
                        waiting_for_continue = False
                    elif event.key == pygame.K_ESCAPE:
                        total_game_time = time.time() - game_start_time
                        try:
                            db_cursor.execute('UPDATE players SET total_game_time = ? WHERE id = ?',
                                              (total_game_time, player_id))
                            conn.commit()
                        except sqlite3.Error as e:
                            print(f"Ошибка обновления времени игры: {e}")
                        game_state = "start_screen"
                        maze = None
                        player_id = None
                        waiting_for_continue = False

        elif game_state == "score_screen":
            screen.fill(BLACK)
            try:
                db_cursor.execute(
                    'SELECT id, name, total_score, state_self_assessment, age, total_game_time FROM players ORDER BY total_score DESC LIMIT 10')
                records = db_cursor.fetchall()
            except sqlite3.Error as e:
                print(f"Ошибка получения таблицы рекордов: {e}")
                records = []

            y_offset = 50
            title_text = font_large.render("Таблица рекордов", True, WHITE)
            screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 10))
            for record in records:
                time_str = f"{int(record[5])} сек" if record[5] is not None else "N/A"
                record_text = font_small.render(
                    f"{record[1]}: {record[2]} очков | Состояние: {record[3]} | Возраст: {record[4]} | Время игры: {time_str}",
                    True, WHITE)
                screen.blit(record_text, (50, y_offset))
                y_offset += 30

            return_button = draw_button(screen, pygame.Rect(WIDTH - 200, HEIGHT - 60, 180, 50),
                                        "Вернуться", font_small, BLACK, WHITE)
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if return_button.collidepoint(event.pos):
                        game_state = "game" if maze else "start_screen"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        game_state = "game" if maze else "start_screen"

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    try:
        conn.close()
    except sqlite3.Error as e:
        print(f"Ошибка закрытия базы данных: {e}")


if __name__ == "__main__":
    main()
