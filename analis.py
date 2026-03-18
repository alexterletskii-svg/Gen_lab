import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, jsonify, send_file
import json
import io
import csv
import webview
import threading
import sys

app = Flask(__name__)

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('game_diagnostics.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/players')
def players():
    conn = get_db_connection()
    players_data = conn.execute('''
        SELECT name, age, total_score, level_reached, total_game_time, state_self_assessment
        FROM players
        ORDER BY name
    ''').fetchall()
    conn.close()
    return render_template('players.html', players=players_data)

# @app.route('/player/<name>')
# def player_analysis(name):
#     conn = get_db_connection()
#     # Получение общей информации об игроке
#     player_data = conn.execute('''
#         SELECT age, total_game_time, level_reached, total_score, avg_reaction_time, total_errors, state_self_assessment
#         FROM players
#         WHERE name = ?
#     ''', (name,)).fetchone()
#     # Получение статистики по уровням
#     level_data = conn.execute('''
#         SELECT level, completion_time, score, reaction_time_avg, errors_count, pause_duration
#         FROM level_stats
#         WHERE player_id = (SELECT player_id FROM players WHERE name = ?)
#         ORDER BY level
#     ''', (name,)).fetchall()
#     # Получение ответов на анкету
#     answers_data = conn.execute('''
#         SELECT q.question_text, a.answer_text
#         FROM answers a
#         JOIN questions q ON a.question_id = q.question_id
#         WHERE a.player_id = (SELECT player_id FROM players WHERE name = ?)
#         ORDER BY q.question_id
#     ''', (name,)).fetchall()
#     conn.close()
#     # Подготовка данных для графика
#     level_chart_data = {
#         'levels': [row['level'] for row in level_data],
#         'times': [row['completion_time'] if row['completion_time'] is not None else 0 for row in level_data]
#     }
#     return render_template('player_analysis.html', player=player_data, name=name, levels=level_data,
#                          answers=answers_data, chart_data=json.dumps(level_chart_data))

@app.route('/player/<name>')
def player_analysis(name):
    conn = get_db_connection()
    # Получение общей информации об игроке
    player_data = conn.execute('''
        SELECT age, total_game_time, level_reached, total_score, avg_reaction_time, total_errors, state_self_assessment
        FROM players 
        WHERE name = ?
    ''', (name,)).fetchone()
    # Получение статистики по уровням
    level_data = conn.execute('''
        SELECT level, completion_time, score, reaction_time_avg, errors_count, pause_duration
        FROM level_stats 
        WHERE player_id = (SELECT id FROM players WHERE name = ?)
        ORDER BY level
    ''', (name,)).fetchall()
    # Получение ответов на анкету
    answers_data_raw = conn.execute('''
        SELECT q.question_text, a.answer_text
        FROM answers a
        JOIN questions q ON a.question_id = q.question_id
        WHERE a.player_id = (SELECT id FROM players WHERE name = ?)
        ORDER BY q.question_id
    ''', (name,)).fetchall()
    conn.close()

    # Удаление дубликатов вопросов и ответов
    answers_data = []
    seen_questions = set()
    for answer in answers_data_raw:
        question = answer['question_text']
        if question not in seen_questions:
            answers_data.append(answer)
            seen_questions.add(question)

    # Подготовка данных для графика
    level_chart_data = {
        'levels': [row['level'] for row in level_data],
        'times': [row['completion_time'] if row['completion_time'] is not None else 0 for row in level_data]
    }
    return render_template('player_analysis.html', player=player_data, name=name, levels=level_data,
                           answers=answers_data, chart_data=json.dumps(level_chart_data))
# @app.route('/api/players_data')
# def players_data():
#     conn = get_db_connection()
#     data = conn.execute('SELECT age, avg_reaction_time, total_errors FROM players WHERE age IS NOT NULL').fetchall()
#     conn.close()
#     return jsonify([{'age': row['age'], 'reaction_time': row['avg_reaction_time'], 'errors': row['total_errors']} for row in data])
#

@app.route('/api/players_data')
def players_data():
    conn = get_db_connection()
    data = conn.execute('SELECT age, avg_reaction_time as reaction_time, total_errors FROM players WHERE age IS NOT NULL').fetchall()
    conn.close()
    return jsonify([{'age': row['age'], 'reaction_time': row['reaction_time'], 'errors': row['total_errors']} for row in data])

@app.route('/compare', methods=['GET', 'POST'])
def compare_players():
    conn = get_db_connection()
    if request.method == 'POST':
        player_names = request.form.getlist('players')
        if not player_names:
            return render_template('compare_players.html', error="Пожалуйста, выберите хотя бы одного игрока.",
                                 players=[])
        players_data = []
        chart_data = {'names': [], 'scores': [], 'game_times': [], 'levels': []}
        for name in player_names:
            player = conn.execute('''
                SELECT name, age, total_game_time, level_reached, total_score, avg_reaction_time, total_errors, state_self_assessment
                FROM players 
                WHERE name = ?
            ''', (name,)).fetchone()
            if player:
                players_data.append(player)
                chart_data['names'].append(player['name'])
                chart_data['scores'].append(player['total_score'] if player['total_score'] else 0)
                chart_data['game_times'].append(player['total_game_time'] if player['total_game_time'] else 0)
                chart_data['levels'].append(player['level_reached'] if player['level_reached'] else 0)
        conn.close()
        return render_template('compare_players.html', players=players_data, chart_data=json.dumps(chart_data))
    all_players = conn.execute('SELECT name FROM players ORDER BY name').fetchall()
    conn.close()
    return render_template('compare_players.html', all_players=all_players)

@app.route('/export_compare', methods=['POST'])
def export_compare():
    player_names = request.form.getlist('players')
    if not player_names:
        return jsonify({'error': 'No players selected'}), 400
    conn = get_db_connection()
    players_data = []
    for name in player_names:
        player = conn.execute('''
            SELECT name, age, total_game_time, level_reached, total_score, avg_reaction_time, total_errors, state_self_assessment
            FROM players 
            WHERE name = ?
        ''', (name,)).fetchone()
        if player:
            players_data.append({
                'Имя': player['name'],
                'Возраст': player['age'] if player['age'] else 'N/A',
                'Общее время игры (сек)': round(player['total_game_time'], 1) if player['total_game_time'] else 'N/A',
                'Достигнутый уровень': player['level_reached'] if player['level_reached'] else 'N/A',
                'Общий счёт': player['total_score'] if player['total_score'] else 'N/A',
                'Среднее время реакции (сек)': round(player['avg_reaction_time'], 3) if player['avg_reaction_time'] else 'N/A',
                'Общее количество ошибок': player['total_errors'] if player['total_errors'] else 'N/A',
                'Самооценка состояния': player['state_self_assessment'] if player['state_self_assessment'] else 'N/A'
            })
    conn.close()
    output = io.StringIO()
    writer = csv.DictWriter(output,
                          fieldnames=['Имя', 'Возраст', 'Общее время игры (сек)', 'Достигнутый уровень', 'Общий счёт',
                                      'Среднее время реакции (сек)', 'Общее количество ошибок',
                                      'Самооценка состояния'])
    writer.writeheader()
    for player in players_data:
        writer.writerow(player)
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='compare_players.csv'
    )

@app.route('/export_player/<name>')
def export_player(name):
    conn = get_db_connection()
    player = conn.execute('''
        SELECT name, age, total_game_time, level_reached, total_score, avg_reaction_time, total_errors, state_self_assessment
        FROM players 
        WHERE name = ?
    ''', (name,)).fetchone()
    level_data = conn.execute('''
        SELECT level, completion_time, score, reaction_time_avg, errors_count, pause_duration
        FROM level_stats 
        WHERE player_id = (SELECT player_id FROM players WHERE name = ?)
        ORDER BY level
    ''', (name,)).fetchall()
    answers_data = conn.execute('''
        SELECT q.question_text, a.answer_text
        FROM answers a
        JOIN questions q ON a.question_id = q.question_id
        WHERE a.player_id = (SELECT player_id FROM players WHERE name = ?)
        ORDER BY q.question_id
    ''', (name,)).fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Общая информация'])
    writer.writerow(['Имя', player['name']])
    writer.writerow(['Возраст', player['age'] if player['age'] else 'N/A'])
    writer.writerow(['Общее время игры (сек)', round(player['total_game_time'], 1) if player['total_game_time'] else 'N/A'])
    writer.writerow(['Достигнутый уровень', player['level_reached'] if player['level_reached'] else 'N/A'])
    writer.writerow(['Общий счёт', player['total_score'] if player['total_score'] else 'N/A'])
    writer.writerow(['Среднее время реакции (сек)',
                    round(player['avg_reaction_time'], 3) if player['avg_reaction_time'] else 'N/A'])
    writer.writerow(['Общее количество ошибок', player['total_errors'] if player['total_errors'] else 'N/A'])
    writer.writerow(['Самооценка состояния', player['state_self_assessment'] if player['state_self_assessment'] else 'N/A'])
    writer.writerow([])
    writer.writerow(['Статистика по уровням'])
    if level_data:
        writer.writerow(['Уровень', 'Время прохождения (сек)', 'Счёт', 'Среднее время реакции (сек)', 'Количество ошибок',
                        'Время паузы (сек)'])
        for level in level_data:
            writer.writerow([
                level['level'],
                round(level['completion_time'], 1) if level['completion_time'] else 'N/A',
                level['score'] if level['score'] else 'N/A',
                round(level['reaction_time_avg'], 3) if level['reaction_time_avg'] else 'N/A',
                level['errors_count'] if level['errors_count'] else 'N/A',
                round(level['pause_duration'], 1) if level['pause_duration'] else 'N/A'
            ])
    else:
        writer.writerow(['Данные по уровням отсутствуют'])
    writer.writerow([])
    writer.writerow(['Ответы на анкету'])
    if answers_data:
        writer.writerow(['Вопрос', 'Ответ'])
        for answer in answers_data:
            writer.writerow([answer['question_text'], answer['answer_text']])
    else:
        writer.writerow(['Ответы на анкету отсутствуют'])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'player_{name}.csv'
    )

# @app.route('/levels')
# def level_analysis():
#     conn = get_db_connection()
#     level_data = conn.execute('''
#         SELECT level, COUNT(*) as count, AVG(completion_time) as avg_time,
#                AVG(score) as avg_score, AVG(reaction_time_avg) as avg_reaction,
#                AVG(errors_count) as avg_errors, AVG(pause_duration) as avg_pause
#         FROM level_stats
#         GROUP BY level
#         ORDER BY level
#     ''').fetchall()
#     conn.close()
#     chart_data = {
#         'levels': [row['level'] for row in level_data],
#         'avg_times': [row['avg_time'] if row['avg_time'] is not None else 0 for row in level_data],
#         'avg_scores': [row['avg_score'] if row['avg_score'] is not None else 0 for row in level_data]
#     }
#     return render_template('level_analysis.html', levels=level_data, chart_data=json.dumps(chart_data))


@app.route('/levels')
def level_analysis():
    conn = get_db_connection()
    level_data = conn.execute('''
        SELECT level, COUNT(*) as count, AVG(completion_time) as avg_time,
               AVG(score) as avg_score, AVG(reaction_time_avg) as avg_reaction,
               AVG(errors_count) as avg_errors, AVG(pause_duration) as avg_pause
        FROM level_stats
        GROUP BY level
        ORDER BY level
    ''').fetchall()

    # Рассчитываем общие метрики для всех уровней
    total_metrics_data = conn.execute('''
        SELECT AVG(completion_time) as total_time,
               AVG(score) as avg_score,
               AVG(reaction_time_avg) as avg_reaction,
               AVG(errors_count) as avg_errors
        FROM level_stats
    ''').fetchone()
    conn.close()

    # Формируем словарь с общими метриками
    total_metrics = {
        'total_time': total_metrics_data['total_time'],
        'avg_score': total_metrics_data['avg_score'],
        'avg_reaction': total_metrics_data['avg_reaction'],
        'avg_errors': total_metrics_data['avg_errors']
    }

    # Подготавливаем данные для графиков
    chart_data = {
        'levels': [row['level'] for row in level_data],
        'avg_times': [row['avg_time'] if row['avg_time'] is not None else 0 for row in level_data],
        'avg_scores': [row['avg_score'] if row['avg_score'] is not None else 0 for row in level_data],
        'avg_reactions': [row['avg_reaction'] if row['avg_reaction'] is not None else 0 for row in level_data],
        'avg_errors': [row['avg_errors'] if row['avg_errors'] is not None else 0 for row in level_data]
    }

    return render_template('level_analysis.html', levels=level_data, chart_data=json.dumps(chart_data),
                           total_metrics=total_metrics)


@app.route('/api/players', methods=['GET'])
def api_players():
    search_term = request.args.get('search', '')
    conn = get_db_connection()
    if search_term:
        players_data = conn.execute('''
            SELECT name, age, total_score, level_reached, total_game_time, state_self_assessment
            FROM players
            WHERE name LIKE ?
            ORDER BY name
        ''', ('%' + search_term + '%',)).fetchall()
    else:
        players_data = conn.execute('''
            SELECT name, age, total_score, level_reached, total_game_time, state_self_assessment
            FROM players
            ORDER BY name
        ''').fetchall()
    conn.close()
    players_list = []
    for player in players_data:
        players_list.append({
            'name': player['name'],
            'age': player['age'] if player['age'] else 'N/A',
            'total_score': player['total_score'] if player['total_score'] else 'N/A',
            'level_reached': player['level_reached'] if player['level_reached'] else 'N/A',
            'total_game_time': round(player['total_game_time'], 1) if player['total_game_time'] else 'N/A',
            'state_self_assessment': player['state_self_assessment'] if player['state_self_assessment'] else 'N/A'
        })
    return jsonify(players_list)

@app.route('/statistics')
def statistics():
    conn = get_db_connection()
    total_players = conn.execute('SELECT COUNT(*) FROM players').fetchone()[0]
    avg_age = conn.execute('SELECT AVG(age) FROM players WHERE age IS NOT NULL').fetchone()[0]
    avg_game_time = conn.execute('SELECT AVG(total_game_time) FROM players WHERE total_game_time IS NOT NULL').fetchone()[0]
    avg_level = conn.execute('SELECT AVG(level_reached) FROM players WHERE level_reached IS NOT NULL').fetchone()[0]
    avg_score = conn.execute('SELECT AVG(total_score) FROM players WHERE total_score IS NOT NULL').fetchone()[0]
    avg_reaction = conn.execute('SELECT AVG(avg_reaction_time) FROM players WHERE avg_reaction_time IS NOT NULL').fetchone()[0]
    avg_errors = conn.execute('SELECT AVG(total_errors) FROM players WHERE total_errors IS NOT NULL').fetchone()[0]
    conn.close()
    stats = {
        'total_players': total_players,
        'avg_age': round(avg_age, 1) if avg_age else 'N/A',
        'avg_game_time': round(avg_game_time, 1) if avg_game_time else 'N/A',
        'avg_level': round(avg_level, 1) if avg_level else 'N/A',
        'avg_score': round(avg_score, 1) if avg_score else 'N/A',
        'avg_reaction': round(avg_reaction, 3) if avg_reaction else 'N/A',
        'avg_errors': round(avg_errors, 1) if avg_errors else 'N/A'
    }
    return jsonify(stats)


@app.route('/questions')
def questions_management():
    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM questions ORDER BY question_id').fetchall()
    conn.close()
    return render_template('question_management.html', questions=questions)


@app.route('/add_question', methods=['POST'])
def add_question():
    question_text = request.form.get('question_text')
    answer_options = request.form.get('answer_options')
    options_list = [opt.strip() for opt in answer_options.split(',') if opt.strip()]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO questions (question_text) VALUES (?)', (question_text,))
    question_id = cursor.lastrowid

    for option in options_list:
        cursor.execute('INSERT INTO answer_options (question_id, option_text) VALUES (?, ?)', (question_id, option))

    conn.commit()
    conn.close()
    return redirect('/questions')


@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    conn = get_db_connection()
    if request.method == 'POST':
        question_text = request.form.get('question_text')
        answer_options = request.form.get('answer_options')
        options_list = [opt.strip() for opt in answer_options.split(',') if opt.strip()]

        conn.execute('UPDATE questions SET question_text = ? WHERE question_id = ?', (question_text, question_id))
        conn.execute('DELETE FROM answer_options WHERE question_id = ?', (question_id,))

        for option in options_list:
            conn.execute('INSERT INTO answer_options (question_id, option_text) VALUES (?, ?)', (question_id, option))

        conn.commit()
        conn.close()
        return redirect('/questions')
    else:
        question = conn.execute('SELECT * FROM questions WHERE question_id = ?', (question_id,)).fetchone()
        options = conn.execute('SELECT * FROM answer_options WHERE question_id = ?', (question_id,)).fetchall()
        conn.close()
        return render_template('edit_question.html', question=question, options=options)


@app.route('/delete_question/<int:question_id>')
def delete_question(question_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM questions WHERE question_id = ?', (question_id,))
    conn.execute('DELETE FROM answer_options WHERE question_id = ?', (question_id,))
    conn.execute('DELETE FROM answers WHERE question_id = ?', (question_id,))
    conn.commit()
    conn.close()
    return redirect('/questions')
# Маршрут для отображения страницы дашборда
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# API для получения данных по уровням (среднее время и ошибки)
@app.route('/api/levels_data')
def levels_data():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT level, 
               AVG(completion_time) as avg_time, 
               AVG(errors_count) as avg_errors 
        FROM level_stats 
        GROUP BY level 
        ORDER BY level
    ''').fetchall()
    conn.close()
    return jsonify([{'level': row['level'], 'avg_time': row['avg_time'], 'avg_errors': row['avg_errors']} for row in data])

# API для получения распределения игроков по возрасту
@app.route('/api/age_distribution')
def age_distribution():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT 
            CASE 
                WHEN age BETWEEN 10 AND 18 THEN '10-18'
                WHEN age BETWEEN 19 AND 25 THEN '19-25'
                WHEN age BETWEEN 26 AND 35 THEN '26-35'
                WHEN age >= 36 THEN '36+'
                ELSE 'Не указан'
            END as age_group,
            COUNT(*) as count
        FROM players
        WHERE age IS NOT NULL
        GROUP BY age_group
        ORDER BY age_group
    ''').fetchall()
    conn.close()
    return jsonify([{'age_group': row['age_group'], 'count': row['count']} for row in data])

# API для получения данных по самооценке состояния игроков
@app.route('/api/self_assessment')
def self_assessment():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT state_self_assessment as assessment, COUNT(*) as count
        FROM players
        WHERE state_self_assessment IS NOT NULL
        GROUP BY state_self_assessment
        ORDER BY state_self_assessment
    ''').fetchall()
    conn.close()
    return jsonify([{'assessment': row['assessment'], 'count': row['count']} for row in data])

# API для получения данных по прогрессу игроков на уровнях
@app.route('/api/level_progress')
def level_progress():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT level, COUNT(DISTINCT player_id) as player_count
        FROM level_stats
        GROUP BY level
        ORDER BY level
    ''').fetchall()
    conn.close()
    return jsonify([{'level': row['level'], 'player_count': row['player_count']} for row in data])


def run_flask():
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    webview.create_window(
        title="Анализ данных игры",
        url="http://127.0.0.1:5000/",
        width=1200,
        height=800,
        resizable=True
    )
    webview.start()
    sys.exit()
