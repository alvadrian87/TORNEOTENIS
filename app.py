import sqlite3
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, g, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import functools
from werkzeug.utils import secure_filename

# --- Configuración de la Aplicación Flask ---
app = Flask(__name__, static_folder='static', template_folder='templates') 

# Configuración de Flask-Session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configuración para la subida de archivos
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Configuración de la base de datos y clave secreta
app.config['DATABASE'] = os.path.join(app.instance_path, 'tournament.db')
app.config['SECRET_KEY'] = 'dev_secret_key_para_produccion_cambiar'
os.makedirs(app.instance_path, exist_ok=True)

# --- Decorador para Proteger Rutas ---
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user_id') is None:
            flash('Necesitas iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# --- Funciones de Ayuda para DB ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r', encoding='utf-8') as f: 
        db.cursor().executescript(f.read())
    db.commit()
    print("Base de datos inicializada o actualizada con schema.sql")

def create_initial_admin():
    db = get_db()
    cursor = db.cursor()
    admin_user = db.execute("SELECT id FROM Users WHERE username = 'admin'").fetchone()
    if not admin_user:
        hashed_password = generate_password_hash('password')
        cursor.execute(
            "INSERT INTO Users (username, password_hash, is_admin) VALUES (?, ?, ?)",
            ('admin', hashed_password, 1)
        )
        db.commit()
        print("Usuario 'admin' creado con contraseña 'password'. ¡Cámbiala en producción!")
    else:
        print("El usuario 'admin' ya existe.")

# --- Funciones de Ayuda para Archivos ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# --- Rutas de Autenticación ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        user = db.execute(
            "SELECT * FROM Users WHERE username = ?", (username,)
        ).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash('Inicio de sesión exitoso!', 'success')
            return redirect(url_for('organizer_page'))
        else:
            flash('Nombre de usuario o contraseña incorrectos.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

# --- Rutas de Páginas Web (Vistas) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/organizer')
@login_required
def organizer_page():
    return send_from_directory(os.path.join(app.static_folder, 'organizer'), 'organizer.html')

@app.route('/add_player')
@login_required
def add_player_page():
    print("DEBUG: [add_player_page] Accediendo a la página de añadir jugador.")
    return render_template('add_player.html')

@app.route('/all_matches')
@login_required
def all_matches_page():
    print("DEBUG: [all_matches_page] Accediendo a la página de todos los partidos.")
    return render_template('all_matches.html')

@app.route('/manage_doubles_teams')
@login_required
def manage_doubles_teams_page():
    print("DEBUG: [manage_doubles_teams_page] Accediendo a la página de gestión de equipos de dobles.")
    return render_template('manage_doubles_teams.html')


@app.route('/proximos_partidos')
def proximos_partidos_page():
    return render_template('proximos_partidos.html')

@app.route('/player/<int:player_id>')
def player_profile_page(player_id):
    db = get_db()
    player = db.execute('SELECT * FROM Players WHERE id = ?', (player_id,)).fetchone()
    if player is None:
        return "Jugador no encontrado", 404

    age = None
    if player['birth_date']:
        try:
            today = datetime.today()
            birth_date = datetime.strptime(player['birth_date'], '%Y-%m-%d')
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except (ValueError, TypeError):
            age = None

    matches_db = db.execute(
        '''SELECT m.id, m.date, m.score_text,
                  (p_chal.first_name || ' ' || p_chal.last_name) AS challenger_name,
                  (p_chd.first_name || ' ' || p_chd.last_name) AS challenged_name,
                  (SELECT p.first_name || ' ' || p.last_name FROM Players p WHERE p.id = m.winner_id) AS winner_name
           FROM Matches m
           JOIN Players p_chal ON m.challenger_id = p_chal.id
           JOIN Players p_chd ON m.challenged_id = p_chd.id
           WHERE m.challenger_id = ? OR m.challenged_id = ?
           ORDER BY m.date DESC''', (player_id, player_id)
    ).fetchall()
    matches = [dict(m) for m in matches_db]
    return render_template('player_profile.html', player=player, age=age, matches=matches)

@app.route('/create_player', methods=['POST'])
@login_required
def create_player():
    db = get_db()
    cursor = db.cursor()

    try:
        add_to_bottom = 'add_to_bottom' in request.form
        position_from_form = request.form.get('position')

        if add_to_bottom or not position_from_form:
            last_pos_row = db.execute('SELECT MAX(current_position) as max_pos FROM Players').fetchone()
            position = (last_pos_row['max_pos'] or 0) + 1
        else:
            position = int(position_from_form)
            cursor.execute("UPDATE Players SET current_position = current_position + 1 WHERE current_position >= ?", (position,))

        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = str(datetime.now().timestamp()).replace(".", "") + "_" + filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                photo_filename = unique_filename
        
        password = request.form.get('password')
        password_hash = generate_password_hash(password) if password else generate_password_hash('evolution') 

        cursor.execute(
            """INSERT INTO Players (first_name, last_name, email, password_hash, phone, gender, 
                                     birth_date, location, dominant_hand, backhand_type, racquet, 
                                     photo_url, category, initial_position, current_position)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (request.form['first_name'], request.form['last_name'], request.form['email'], password_hash, 
             request.form.get('phone'), request.form.get('gender'), request.form.get('birth_date'),
             request.form.get('location'), request.form.get('dominant_hand'), request.form.get('backhand_type'),
             request.form.get('racquet'), photo_filename, request.form['category'], position, position)
        )
        db.commit()
    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [create_player] Error de SQLite: {str(e)}")
        flash(f"Error en la base de datos al crear jugador: {e}", 'error')
        return redirect(url_for('add_player_page'))
    except KeyError as e:
        print(f"ERROR: [create_player] Falta un campo requerido en el formulario: {e}")
        flash(f"Error: Falta un campo requerido ({e}). Asegúrate de llenar todos los campos obligatorios (Nombre, Apellido, Email, Categoría).", 'error')
        return redirect(url_for('add_player_page'))
    except Exception as e:
        print(f"ERROR GENERICO: [create_player] Error inesperado: {str(e)}")
        flash(f"Ocurrió un error inesperado al crear el jugador: {str(e)}", 'error')
        return redirect(url_for('add_player_page'))

    flash('Jugador creado exitosamente!', 'success')
    return redirect(url_for('organizer_page'))

# --- API Endpoints ---

@app.route('/api/players', methods=['GET'])
def get_players_api():
    db = get_db()
    players_db = db.execute(
        'SELECT * FROM Players ORDER BY current_position ASC'
    ).fetchall()
    
    players = []
    for p in players_db:
        player_dict = dict(p)
        player_dict['name'] = f"{p['first_name']} {p['last_name']}"
        players.append(player_dict)

    return jsonify(players)

# NUEVOS ENDPOINTS PARA GESTIÓN DE EQUIPOS DE DOBLES
@app.route('/api/doubles_teams', methods=['POST'])
@login_required
def create_doubles_team_api():
    data = request.get_json()
    player1_id = data.get('player1_id')
    player2_id = data.get('player2_id')
    team_name = data.get('team_name')

    if not all([player1_id, player2_id, team_name]):
        return jsonify({"error": "Faltan IDs de jugadores o el nombre del equipo."}), 400
    
    if player1_id == player2_id:
        return jsonify({"error": "Los jugadores de un equipo no pueden ser el mismo."}), 400

    db = get_db()
    cursor = db.cursor()

    try:
        player1 = db.execute('SELECT id, gender FROM Players WHERE id = ?', (player1_id,)).fetchone()
        player2 = db.execute('SELECT id, gender FROM Players WHERE id = ?', (player2_id,)).fetchone()

        if not player1 or not player2:
            return jsonify({"error": "Uno o ambos jugadores no encontrados."}), 404
        
        if player1['gender'] != player2['gender']:
            return jsonify({"error": "Los jugadores deben ser del mismo género para formar un equipo de dobles."}), 400
        
        gender_category = player1['gender'] # 'Masculino' o 'Femenino'

        # --- NUEVA VALIDACIÓN: Verificar si alguno de los jugadores ya está en otro equipo ---
        existing_player_in_team = db.execute(
            '''SELECT t.team_name FROM Teams t
               WHERE (t.player1_id = ? OR t.player2_id = ?) OR (t.player1_id = ? OR t.player2_id = ?)''',
            (player1_id, player1_id, player2_id, player2_id) # Busca si player1 o player2 ya están en cualquier columna
        ).fetchone()

        if existing_player_in_team:
            return jsonify({"error": f"Uno o ambos jugadores ya forman parte del equipo '{existing_player_in_team['team_name']}'."}), 409 # 409 Conflict
        # --- FIN NUEVA VALIDACIÓN ---

        # Verificar si la pareja ya existe (en cualquier orden)
        existing_team = db.execute(
            '''SELECT id FROM Teams WHERE 
               (player1_id = ? AND player2_id = ?) OR (player1_id = ? AND player2_id = ?)''',
            (player1_id, player2_id, player2_id, player1_id)
        ).fetchone()

        if existing_team:
            return jsonify({"error": "Este equipo de dobles ya existe."}), 409
        
        # Obtener la última posición para esta categoría de género
        last_pos_row = db.execute(
            'SELECT MAX(current_position) as max_pos FROM Teams WHERE gender_category = ?',
            (gender_category,)
        ).fetchone()
        position = (last_pos_row['max_pos'] or 0) + 1

        cursor.execute(
            """INSERT INTO Teams (player1_id, player2_id, team_name, gender_category, initial_position, current_position)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (player1_id, player2_id, team_name, gender_category, position, position)
        )
        db.commit()
        return jsonify({"message": "Equipo de dobles creado exitosamente.", "team_id": cursor.lastrowid}), 201

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [create_doubles_team_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al crear equipo de dobles: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [create_doubles_team_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al crear equipo de dobles: {str(e)}"}), 500

@app.route('/api/propose_doubles_challenge', methods=['POST'])
@login_required 
def propose_doubles_challenge_api():
    data = request.get_json()
    print(f"DEBUG: [propose_doubles_challenge_api] Datos recibidos: {data}")
    challenger_team_id = data.get('challengerTeamId')
    challenged_team_id = data.get('challengedTeamId')

    if not all([challenger_team_id, challenged_team_id]):
        print("DEBUG: [propose_doubles_challenge_api] Faltan IDs de equipos.")
        return jsonify({"error": "Faltan IDs de equipos para proponer el desafío."}), 400
    
    if challenger_team_id == challenged_team_id:
        return jsonify({"error": "Un equipo no puede desafiarse a sí mismo."}), 400

    db = get_db()
    cursor = db.cursor()
    inserted_id = None 

    try:
        # CORRECCIÓN: Incluir current_position en la selección para la validación de posición
        challenger_team = db.execute('SELECT id, gender_category, current_position FROM Teams WHERE id = ?', (challenger_team_id,)).fetchone()
        challenged_team = db.execute('SELECT id, gender_category, current_position FROM Teams WHERE id = ?', (challenged_team_id,)).fetchone()

        if not challenger_team or not challenged_team:
            return jsonify({"error": "Uno o ambos equipos no encontrados."}), 404
        
        if challenger_team['gender_category'] != challenged_team['gender_category']:
            return jsonify({"error": "Los equipos deben ser del mismo género para formar un equipo de dobles."}), 400
        
        # Opcional: Re-validar la regla de posición aquí si no lo haces en validate_doubles_challenge_api
        if challenger_team['current_position'] <= challenged_team['current_position']:
             return jsonify({"error": "El equipo desafiante debe estar en una posición inferior al desafiado para proponer el desafío."}), 400

        # Verificar si ya existe un desafío pendiente entre estos dos equipos
        existing_challenge = db.execute(
            '''SELECT id FROM DoublesMatches 
               WHERE (team_a_id = ? AND team_b_id = ?) OR (team_a_id = ? AND team_b_id = ?) 
               AND status = 'pending' ''',
            (challenger_team_id, challenged_team_id, challenged_team_id, challenger_team_id)
        ).fetchone()

        if existing_challenge:
            print(f"DEBUG: [propose_doubles_challenge_api] Desafío de dobles ya existe (ID: {existing_challenge['id']}).")
            return jsonify({"error": "Ya existe un desafío de dobles pendiente entre estos equipos."}), 409

        # CORRECCIÓN: Asegurarse de insertar solo las columnas necesarias, 'date' y 'created_at' son DEFAULT CURRENT_TIMESTAMP
        cursor.execute(
            """INSERT INTO DoublesMatches (team_a_id, team_b_id, status)
               VALUES (?, ?, ?)""",
            (challenger_team_id, challenged_team_id, 'pending')
        )
        inserted_id = cursor.lastrowid
        print(f"DEBUG: [propose_doubles_challenge_api] Intentando COMMIT para challenge_id: {inserted_id}")
        db.commit()
        print(f"DEBUG: [propose_doubles_challenge_api] COMMIT EXITOSO para challenge_id: {inserted_id}")
        return jsonify({"message": "Desafío de dobles propuesto y registrado como pendiente.", "challenge_id": inserted_id}), 201

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [propose_doubles_challenge_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al proponer desafío de dobles: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [propose_doubles_challenge_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al proponer desafío de dobles: {str(e)}"}), 500


@app.route('/api/doubles_teams', methods=['GET'])
@login_required
def get_doubles_teams_api():
    db = get_db()
    gender_filter = request.args.get('gender') # Permite filtrar por género (ej. ?gender=Masculino)

    query = '''
        SELECT t.id, t.player1_id, t.player2_id, t.team_name, t.gender_category, t.current_position, t.initial_position,
               p1.first_name AS p1_first_name, p1.last_name AS p1_last_name,
               p2.first_name AS p2_first_name, p2.last_name AS p2_last_name
        FROM Teams t
        JOIN Players p1 ON t.player1_id = p1.id
        JOIN Players p2 ON t.player2_id = p2.id
    '''
    params = []
    if gender_filter:
        query += ' WHERE t.gender_category = ?'
        params.append(gender_filter)
    
    query += ' ORDER BY t.gender_category ASC, t.current_position ASC' # Ordenar por género y luego por posición

    try:
        teams_db = db.execute(query, params).fetchall()
        teams = []
        for t in teams_db:
            team_dict = dict(t)
            team_dict['player1_name'] = f"{t['p1_first_name']} {t['p1_last_name']}"
            team_dict['player2_name'] = f"{t['p2_first_name']} {t['p2_last_name']}"
            teams.append(team_dict)
        return jsonify(teams), 200
    except sqlite3.Error as e:
        print(f"ERROR DB: [get_doubles_teams_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener equipos de dobles: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_doubles_teams_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener equipos de dobles: {str(e)}"}), 500

# En app.py, dentro de la sección de "API Endpoints"

# NUEVO ENDPOINT: Valida un desafío de dobles
@app.route('/api/validate_doubles_challenge', methods=['POST'])
@login_required 
def validate_doubles_challenge_api():
    data = request.get_json()
    challenger_team_id = data.get('challengerTeamId')
    challenged_team_id = data.get('challengedTeamId')

    if not all([challenger_team_id, challenged_team_id]):
        return jsonify({"error": "Faltan IDs de equipos."}), 400

    db = get_db()
    # Incluir current_position en la selección para la validación de posición
    challenger_team = db.execute('SELECT id, gender_category, current_position FROM Teams WHERE id = ?', (challenger_team_id,)).fetchone()
    challenged_team = db.execute('SELECT id, gender_category, current_position FROM Teams WHERE id = ?', (challenged_team_id,)).fetchone()

    if not challenger_team or not challenged_team:
        return jsonify({"error": "Uno o ambos equipos no encontrados."}), 404
    
    if challenger_team['gender_category'] != challenged_team['gender_category']:
        return jsonify({"error": "Los equipos deben ser del mismo género para formar un equipo de dobles."}), 400

    challenger_pos = challenger_team['current_position']
    challenged_pos = challenged_team['current_position']
    
    # Obtener el total de equipos para la categoría de género del desafiante
    # Esto es necesario para la regla del "Último jugador"
    total_teams_in_category = db.execute(
        'SELECT COUNT(*) FROM Teams WHERE gender_category = ?', 
        (challenger_team['gender_category'],)
    ).fetchone()[0]

    is_valid = False
    message = "Desafío de dobles no permitido."

    # Reglas de desafío (aplicadas a dobles)
    if challenger_pos == 1: # Puesto 1
        if challenged_pos >= 2 and challenged_pos <= 6:
            is_valid = True
            message = "Desafío permitido: Puesto 1 puede desafiar a 2-6."
        else:
            message = "Puesto 1 solo puede desafiar a equipos entre el puesto 2 y 6."
    elif challenger_pos == 2: # Puesto 2
        if challenged_pos in [1, 3, 4]:
            is_valid = True
            message = "Desafío permitido: Puesto 2 puede desafiar a 1, 3 y 4."
        else:
            message = "Puesto 2 solo puede desafiar a equipos en los puestos 1, 3 y 4."
    elif challenger_pos == 3: # Puesto 3
        if challenged_pos in [1, 2, 4]:
            is_valid = True
            message = "Desafío permitido: Puesto 3 puede desafiar a 1, 2 y 4."
        else:
            message = "Puesto 3 solo puede desafiar a equipos en los puestos 1, 2 y 4."
    elif challenger_pos == total_teams_in_category: # Último equipo en su categoría
        if challenged_pos >= (total_teams_in_category - 5) and challenged_pos < total_teams_in_category: # Los 5 de arriba
            is_valid = True
            message = "Desafío permitido: Último equipo puede desafiar a los 5 de arriba."
        else:
            message = "El último equipo solo puede desafiar a los 5 equipos inmediatamente superiores."
    elif challenger_pos >= 4: # Puesto 4 en adelante (no el último)
        # Puede desafiar a los 3 equipos inmediatamente por encima
        if challenged_pos >= (challenger_pos - 3) and challenged_pos < challenger_pos:
            is_valid = True
            message = "Desafío permitido: Puede desafiar a los 3 equipos inmediatamente superiores."
        else:
            message = "Solo puedes desafiar a los 3 equipos inmediatamente superiores."
    
    if is_valid:
        return jsonify({"valid": True, "message": message}), 200
    else:
        return jsonify({"valid": False, "message": message}), 200

# NUEVO ENDPOINT: Obtiene los desafíos de dobles pendientes
@app.route('/api/pending_doubles_challenges', methods=['GET'])
@login_required 
def get_pending_doubles_challenges_api():
    db = get_db()
    try:
        # CORRECCIÓN: La consulta debe ser a DoublesMatches y seleccionar team_a_id, team_b_id
        pending_doubles_challenges_db = db.execute(
            '''SELECT dc.id, dc.date, dc.team_a_id, dc.team_b_id, dc.status, dc.created_at,
                      t_a.team_name AS challenger_team_name, t_b.team_name AS challenged_team_name
               FROM DoublesMatches dc
               JOIN Teams t_a ON dc.team_a_id = t_a.id
               JOIN Teams t_b ON dc.team_b_id = t_b.id
               WHERE dc.status = 'pending'
               ORDER BY dc.created_at DESC'''
        ).fetchall()

        challenges = []
        for pc in pending_doubles_challenges_db:
            challenge_dict = dict(pc)
            challenge_dict['challenger_team_id'] = pc['team_a_id'] # Necesario para el frontend
            challenge_dict['challenged_team_id'] = pc['team_b_id'] # Necesario para el frontend
            challenge_dict['challenger_team_name'] = pc['challenger_team_name']
            challenge_dict['challenged_team_name'] = pc['challenged_team_name']
            challenges.append(challenge_dict)

        return jsonify(challenges), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_pending_doubles_challenges_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener desafíos de dobles pendientes: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_pending_doubles_challenges_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener desafíos de dobles pendientes: {str(e)}"}), 500

@app.route('/api/doubles_match_result', methods=['POST'])
@login_required 
def post_doubles_match_result_api():
    data = request.get_json()
    challenger_team_id = int(data.get('challengerTeamId'))
    challenged_team_id = int(data.get('challengedTeamId'))
    sets = data.get('sets')
    challenge_id = data.get('challengeId') # ID del desafío pendiente, si viene de uno

    if not all([challenger_team_id, challenged_team_id, sets]) or not (2 <= len(sets) <= 3):
        return jsonify({"error": "Datos de partido de dobles incompletos o número de sets incorrecto."}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        challenger_team = db.execute('SELECT * FROM Teams WHERE id = ?', (challenger_team_id,)).fetchone()
        challenged_team = db.execute('SELECT * FROM Teams WHERE id = ?', (challenged_team_id,)).fetchone()

        if not challenger_team or not challenged_team:
            return jsonify({"error": "Uno o ambos equipos no encontrados."}), 404

        chal_sets_won = sum(1 for s in sets if s[0] > s[1])
        chd_sets_won = len(sets) - chal_sets_won
        
        if not ((chal_sets_won == 2 and chd_sets_won < 2) or (chd_sets_won == 2 and chal_sets_won < 2)):
            return jsonify({"error": "Resultado inválido para dobles: un equipo debe ganar 2 sets."}), 400

        score_text = ", ".join([f"{s[0]}-{s[1]}" for s in sets])
        
        challenger_won_match = chal_sets_won > chd_sets_won # Si el equipo A (challenger) ganó el partido
        winner_team_id = challenger_team_id if challenger_won_match else challenged_team_id
        loser_team_id = challenged_team_id if challenger_won_match else challenger_team_id

        positions_swapped = False
        new_challenger_team_pos, new_challenged_team_pos = challenger_team['current_position'], challenged_team['current_position']

        # Lógica de intercambio de posiciones para dobles
        if challenger_won_match and challenger_team['current_position'] > challenged_team['current_position']:
            # Si el equipo desafiante ganó y estaba en una posición numérica mayor (peor ranking)
            new_challenger_team_pos, new_challenged_team_pos = challenged_team['current_position'], challenger_team['current_position']
            positions_swapped = True
        
        # Actualizar posiciones de los equipos
        cursor.execute("UPDATE Teams SET current_position = ? WHERE id = ?", (new_challenger_team_pos, challenger_team_id))
        cursor.execute("UPDATE Teams SET current_position = ? WHERE id = ?", (new_challenged_team_pos, challenged_team_id))
        
        # Insertar el partido de dobles en la tabla DoublesMatches
        cursor.execute(
            """INSERT INTO DoublesMatches (date, team_a_id, team_b_id, winner_team_id, loser_team_id, score_text, is_team_a_winner, positions_swapped)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), challenger_team_id, challenged_team_id, winner_team_id, loser_team_id, score_text, challenger_won_match, positions_swapped)
        )
        
        # Si el partido viene de un desafío pendiente, actualizar su estado
        if challenge_id:
            cursor.execute("UPDATE DoublesMatches SET status = 'played' WHERE id = ?", (challenge_id,))
            print(f"DEBUG: [post_doubles_match_result_api] Desafío de dobles pendiente {challenge_id} marcado como 'played'.")
        
        db.commit()
        return jsonify({"message": "Resultado de dobles procesado exitosamente y posiciones actualizadas."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [post_doubles_match_result_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al procesar resultado de dobles: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [post_doubles_match_result_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al procesar resultado de dobles: {str(e)}"}), 500


@app.route('/api/all_matches', methods=['GET'])
@login_required # Proteger este endpoint si solo el organizador debe ver todos los partidos
def get_all_matches_api():
    db = get_db()
    try:
        matches_db = db.execute(
            '''SELECT m.id, m.date, m.score_text,
                      p_chal.first_name AS challenger_first_name, p_chal.last_name AS challenger_last_name,
                      p_chd.first_name AS challenged_first_name, p_chd.last_name AS challenged_last_name,
                      p_winner.first_name AS winner_first_name, p_winner.last_name AS winner_last_name,
                      p_loser.first_name AS loser_first_name, p_loser.last_name AS loser_last_name,
                      'single' AS match_type -- Añadir tipo de partido
               FROM Matches m
               JOIN Players p_chal ON m.challenger_id = p_chal.id
               JOIN Players p_chd ON m.challenged_id = p_chd.id
               JOIN Players p_winner ON m.winner_id = p_winner.id
               JOIN Players p_loser ON m.loser_id = p_loser.id
               ORDER BY m.date DESC'''
        ).fetchall()

        matches = []
        for m in matches_db:
            match_dict = dict(m)
            match_dict['challenger_name'] = f"{m['challenger_first_name']} {m['challenger_last_name']}"
            match_dict['challenged_name'] = f"{m['challenged_first_name']} {m['challenged_last_name']}"
            match_dict['winner_name'] = f"{m['winner_first_name']} {m['winner_last_name']}"
            match_dict['loser_name'] = f"{m['loser_first_name']} {m['loser_last_name']}"
            matches.append(match_dict)

        return jsonify(matches), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_all_matches_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener todos los partidos: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_all_matches_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener todos los partidos: {str(e)}"}), 500

@app.route('/api/all_doubles_matches', methods=['GET'])
@login_required # Proteger este endpoint si solo el organizador debe ver todos los partidos de dobles
def get_all_doubles_matches_api():
    db = get_db()
    try:
        doubles_matches_db = db.execute(
            '''SELECT dm.id, dm.date, dm.score_text, dm.winner_team_id, dm.loser_team_id,
                      t_a.team_name AS team_a_name, t_b.team_name AS team_b_name,
                      t_winner.team_name AS winner_team_name, t_loser.team_name AS loser_team_name
               FROM DoublesMatches dm
               JOIN Teams t_a ON dm.team_a_id = t_a.id
               JOIN Teams t_b ON dm.team_b_id = t_b.id
               JOIN Teams t_winner ON dm.winner_team_id = t_winner.id
               JOIN Teams t_loser ON dm.loser_team_id = t_loser.id
               ORDER BY dm.date DESC''' # Ordenar por fecha de más reciente a más antiguo
        ).fetchall()

        matches = []
        for dm in doubles_matches_db:
            match_dict = dict(dm)
            match_dict['challenger_name'] = dm['team_a_name']
            match_dict['challenged_name'] = dm['team_b_name']
            match_dict['winner_name'] = dm['winner_team_name']
            match_dict['loser_name'] = dm['loser_team_name']
            matches.append(match_dict)

        return jsonify(matches), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_all_doubles_matches_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener todos los partidos de dobles: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_all_doubles_matches_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener todos los partidos de dobles: {str(e)}"}), 500

@app.route('/api/validate_challenge', methods=['POST'])
@login_required
def validate_challenge_api():
    data = request.get_json()
    challenger_id = data.get('challengerId')
    challenged_id = data.get('challengedId')

    if not all([challenger_id, challenged_id]):
        return jsonify({"error": "Faltan IDs de jugadores."}), 400

    db = get_db()
    all_players_positions = db.execute('SELECT id, current_position FROM Players ORDER BY current_position ASC').fetchall()
    
    challenger_player = next((p for p in all_players_positions if p['id'] == challenger_id), None)
    challenged_player = next((p for p in all_players_positions if p['id'] == challenged_id), None)

    if not challenger_player or not challenged_player:
        return jsonify({"error": "Uno o ambos jugadores no encontrados."}), 404

    challenger_pos = challenger_player['current_position']
    challenged_pos = challenged_player['current_position']
    total_players = len(all_players_positions)

    is_valid = False
    message = "Desafío no permitido."

    # Reglas de desafío
    if challenger_pos == 1: # Puesto 1
        if challenged_pos >= 2 and challenged_pos <= 6:
            is_valid = True
            message = "Desafío permitido: Puesto 1 puede desafiar a 2-6."
        else:
            message = "Puesto 1 solo puede desafiar a jugadores entre el puesto 2 y 6."
    elif challenger_pos == 2: # Puesto 2
        if challenged_pos in [1, 3, 4]:
            is_valid = True
            message = "Desafío permitido: Puesto 2 puede desafiar a 1, 3 y 4."
        else:
            message = "Puesto 2 solo puede desafiar a jugadores en los puestos 1, 3 y 4."
    elif challenger_pos == 3: # Puesto 3
        if challenged_pos in [1, 2, 4]:
            is_valid = True
            message = "Desafío permitido: Puesto 3 puede desafiar a 1, 2 y 4."
        else:
            message = "Puesto 3 solo puede desafiar a jugadores en los puestos 1, 2 y 4."
    elif challenger_pos == total_players: # Último jugador
        if challenged_pos >= (total_players - 5) and challenged_pos < total_players: # Los 5 de arriba
            is_valid = True
            message = "Desafío permitido: Último jugador puede desafiar a los 5 de arriba."
        else:
            message = "El último jugador solo puede desafiar a los 5 jugadores inmediatamente superiores."
    elif challenger_pos >= 4: # Puesto 4 en adelante (no el último)
        # Puede desafiar a los 3 jugadores inmediatamente por encima
        if challenged_pos >= (challenger_pos - 3) and challenged_pos < challenger_pos:
            is_valid = True
            message = "Desafío permitido: Puede desafiar a los 3 jugadores inmediatamente superiores."
        else:
            message = "Solo puedes desafiar a los 3 jugadores inmediatamente superiores."
    
    if is_valid:
        return jsonify({"valid": True, "message": message}), 200
    else:
        return jsonify({"valid": False, "message": message}), 200

@app.route('/api/propose_challenge', methods=['POST'])
@login_required 
def propose_challenge_api():
    data = request.get_json()
    print(f"DEBUG: [propose_challenge_api] Datos recibidos: {data}")
    challenger_id = data.get('challengerId')
    challenged_id = data.get('challengedId')

    if not all([challenger_id, challenged_id]):
        print("DEBUG: [propose_challenge_api] Faltan IDs de jugadores.")
        return jsonify({"error": "Faltan IDs de jugadores para proponer el desafío."}), 400

    db = get_db()
    cursor = db.cursor()
    inserted_id = None 

    try:
        existing_challenge = db.execute(
            '''SELECT id FROM Challenges WHERE challenger_id = ? AND challenged_id = ? AND status = 'pending' ''',
            (challenger_id, challenged_id)
        ).fetchone()

        if existing_challenge:
            print(f"DEBUG: [propose_challenge_api] Desafío ya existe (ID: {existing_challenge['id']}).")
            return jsonify({"error": "Ya existe un desafío pendiente entre estos jugadores."}), 409

        cursor.execute(
            '''INSERT INTO Challenges (challenger_id, challenged_id, status)
               VALUES (?, ?, ?)''',
            (challenger_id, challenged_id, 'pending')
        )
        inserted_id = cursor.lastrowid
        print(f"DEBUG: [propose_challenge_api] Intentando COMMIT para challenge_id: {inserted_id}")
        db.commit()
        print(f"DEBUG: [propose_challenge_api] COMMIT EXITOSO para challenge_id: {inserted_id}")
        return jsonify({"message": "Desafío propuesto y registrado como pendiente.", "challenge_id": inserted_id}), 201

    except sqlite3.Error as e:
        print(f"ERROR DB: [propose_challenge_api] Error de SQLite: {str(e)}")
        db.rollback()
        return jsonify({"error": f"Error de base de datos al proponer desafío: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [propose_challenge_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al proponer desafío: {str(e)}"}), 500

@app.route('/api/pending_challenges', methods=['GET'])
@login_required 
def get_pending_challenges_api():
    db = get_db()
    try:
        pending_challenges_db = db.execute(
            '''SELECT c.id, c.challenger_id, c.challenged_id, c.status, c.created_at,
                      p_chal.first_name AS challenger_first_name, p_chal.last_name AS challenger_last_name,
                      p_chd.first_name AS challenged_first_name, p_chd.last_name AS challenged_last_name
               FROM Challenges c
               JOIN Players p_chal ON c.challenger_id = p_chal.id
               JOIN Players p_chd ON c.challenged_id = p_chd.id
               WHERE c.status = 'pending'
               ORDER BY c.created_at DESC'''
        ).fetchall()

        challenges = []
        for pc in pending_challenges_db:
            challenge_dict = dict(pc)
            challenge_dict['challenger_name'] = f"{pc['challenger_first_name']} {pc['challenger_last_name']}"
            challenge_dict['challenged_name'] = f"{pc['challenged_first_name']} {pc['challenged_last_name']}"
            challenges.append(challenge_dict)

        return jsonify(challenges), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_pending_challenges_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener desafíos pendientes: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_pending_challenges_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener desafíos pendientes: {str(e)}"}), 500


@app.route('/api/match_result', methods=['POST'])
@login_required 
def post_match_result_api():
    data = request.get_json()
    challenger_id = int(data.get('challengerId'))
    challenged_id = int(data.get('challengedId'))
    sets = data.get('sets')
    challenge_id = data.get('challengeId')

    if not all([challenger_id, challenged_id, sets]) or not (2 <= len(sets) <= 3):
        return jsonify({"error": "Datos de partido incompletos o número de sets incorrecto."}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        challenger = db.execute('SELECT * FROM Players WHERE id = ?', (challenger_id,)).fetchone()
        challenged = db.execute('SELECT * FROM Players WHERE id = ?', (challenged_id,)).fetchone()

        chal_sets_won = sum(1 for s in sets if s[0] > s[1])
        chd_sets_won = len(sets) - chal_sets_won
        
        if not ((chal_sets_won == 2 and chd_sets_won < 2) or (chd_sets_won == 2 and chal_sets_won < 2)):
            return jsonify({"error": "Resultado inválido: un jugador debe ganar 2 sets."}), 400

        score_text = ", ".join([f"{s[0]}-{s[1]}" for s in sets])
        
        challenger_won_match = chal_sets_won > chd_sets_won
        winner_id = challenger_id if challenger_won_match else challenged_id
        loser_id = challenged_id if challenger_won_match else challenger_id

        positions_swapped = False
        final_challenger_pos = challenger['current_position']
        final_challenged_pos = challenged['current_position']

        # Regla 1: Challenger gana y es de menor ranking (mayor número de posición)
        if challenger_won_match and challenger['current_position'] > challenged['current_position']:
            final_challenger_pos = challenged['current_position']
            final_challenged_pos = challenger['current_position']
            positions_swapped = True
            print(f"DEBUG: Standard swap - Challenger {challenger_id} won against {challenged_id}. Positions swapped.")

        # Regla 2: Challenger es Puesto 1 y pierde (intercambia con el desafiado)
        elif not challenger_won_match and challenger['current_position'] == 1:
            final_challenger_pos = challenged['current_position']
            final_challenged_pos = challenger['current_position']
            positions_swapped = True
            print(f"DEBUG: Puesto 1 lost - Challenger {challenger_id} (P1) lost to {challenged_id}. Positions swapped.")

        cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (final_challenger_pos, challenger_id))
        cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (final_challenged_pos, challenged_id))
        
        cursor.execute(
            """INSERT INTO Matches (date, challenger_id, challenged_id, winner_id, loser_id, score_text, is_challenger_winner, positions_swapped)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), challenger_id, challenged_id, winner_id, loser_id, score_text, challenger_won_match, positions_swapped)
        )
        
        if challenge_id:
            cursor.execute("UPDATE Challenges SET status = 'played' WHERE id = ?", (challenge_id,))
            print(f"DEBUG: [post_match_result_api] Desafío pendiente {challenge_id} marcado como 'played'.")
        
        db.commit()
        return jsonify({"message": "Resultado procesado exitosamente."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [post_match_result_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error en la base de datos: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [post_match_result_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al procesar el resultado: {str(e)}"}), 500

@app.route('/api/reset_leaderboard', methods=['POST'])
@login_required 
def reset_leaderboard_api():
    db = get_db()
    try:
        db.execute("UPDATE Players SET initial_position = current_position, points = 0")
        db.commit()
        return jsonify({"message": "Tabla reiniciada para un nuevo período exitosamente."}), 200
    except sqlite3.Error as e:
        print(f"ERROR DB: [reset_leaderboard_api] Error de SQLite: {str(e)}")
        db.rollback()
        return jsonify({"error": f"Error al reiniciar la tabla: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [reset_leaderboard_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al reiniciar la tabla: {str(e)}"}), 500

@app.route('/api/matches/<int:match_id>/delete', methods=['POST'])
@login_required 
def delete_match_api(match_id):
    db = get_db()
    cursor = db.cursor()
    try:
        match = db.execute('SELECT challenger_id, challenged_id, winner_id, loser_id, positions_swapped FROM Matches WHERE id = ?', (match_id,)).fetchone()
        if not match:
            return jsonify({"error": "Partido no encontrado."}), 404

        if match['positions_swapped']:
            winner_id = match['winner_id']
            loser_id = match['loser_id']
            
            winner_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (winner_id,)).fetchone()['current_position']
            loser_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (loser_id,)).fetchone()['current_position']

            cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (loser_pos, winner_id))
            cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (winner_pos, loser_id))

        cursor.execute('DELETE FROM Matches WHERE id = ?', (match_id,))
        db.commit()
        return jsonify({"message": "Partido eliminado y posiciones revertidas exitosamente."}), 200
    except sqlite3.Error as e:
        print(f"ERROR DB: [delete_match_api] Error de SQLite: {str(e)}")
        db.rollback()
        return jsonify({"error": f"Error de base de datos al eliminar el partido: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [delete_match_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al eliminar el partido: {str(e)}"}), 500

@app.route('/api/challenges/<int:challenge_id>/cancel', methods=['POST'])
@login_required 
def cancel_challenge_api(challenge_id):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE Challenges SET status = 'cancelled' WHERE id = ? AND status = 'pending'", (challenge_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Desafío no encontrado o no está pendiente."}), 404
        return jsonify({"message": "Desafío cancelado exitosamente."}), 200
    except sqlite3.Error as e:
        print(f"ERROR DB: [cancel_challenge_api] Error de SQLite: {str(e)}")
        db.rollback()
        return jsonify({"error": f"Error al cancelar desafío: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [cancel_challenge_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al cancelar desafío: {str(e)}"}), 500

@app.route('/api/players/<int:player_id>/history', methods=['GET'])
@login_required 
def get_player_history_api(player_id):
    db = get_db()
    try:
        # Obtener partidos individuales del jugador
        individual_matches_db = db.execute(
            '''SELECT m.id, m.date, m.score_text, m.winner_id, m.loser_id, m.challenger_id, m.challenged_id,
                      p_challenger.first_name AS challenger_first_name, p_challenger.last_name AS challenger_last_name,
                      p_challenged.first_name AS challenged_first_name, p_challenged.last_name AS challenged_last_name,
                      p_winner.first_name AS winner_first_name, p_winner.last_name AS winner_last_name,
                      p_loser.first_name AS loser_first_name, p_loser.last_name AS loser_last_name,
                      'single' AS match_type -- Añadir tipo de partido
               FROM Matches m
               JOIN Players p_challenger ON m.challenger_id = p_challenger.id
               JOIN Players p_challenged ON m.challenged_id = p_challenged.id
               JOIN Players p_winner ON m.winner_id = p_winner.id
               JOIN Players p_loser ON m.loser_id = p_loser.id
               WHERE m.challenger_id = ? OR m.challenged_id = ?''',
            (player_id, player_id)
        ).fetchall()

        # Obtener partidos de dobles del jugador
        doubles_matches_db = db.execute(
            '''SELECT dm.id, dm.date, dm.score_text, dm.winner_team_id, dm.loser_team_id,
                      t_a.team_name AS team_a_name, t_b.team_name AS team_b_name,
                      t_winner.team_name AS winner_team_name, t_loser.team_name AS loser_team_name,
                      'doubles' AS match_type -- Añadir tipo de partido
               FROM DoublesMatches dm
               JOIN Teams t_a ON dm.team_a_id = t_a.id
               JOIN Teams t_b ON dm.team_b_id = t_b.id
               JOIN Teams t_winner ON dm.winner_team_id = t_winner.id
               JOIN Teams t_loser ON dm.loser_team_id = t_loser.id
               WHERE t_a.player1_id = ? OR t_a.player2_id = ? OR t_b.player1_id = ? OR t_b.player2_id = ?''',
            (player_id, player_id, player_id, player_id)
        ).fetchall()

        all_matches = []

        for m in individual_matches_db:
            match_dict = dict(m)
            match_dict['challenger_name'] = f"{m['challenger_first_name']} {m['challenger_last_name']}"
            match_dict['challenged_name'] = f"{m['challenged_first_name']} {m['challenged_last_name']}"
            match_dict['winner_name'] = f"{m['winner_first_name']} {m['winner_last_name']}"
            match_dict['loser_name'] = f"{m['loser_first_name']} {m['loser_last_name']}"
            all_matches.append(match_dict)
        
        for dm in doubles_matches_db:
            match_dict = dict(dm)
            match_dict['challenger_name'] = dm['team_a_name'] # Para consistencia en el frontend
            match_dict['challenged_name'] = dm['team_b_name'] # Para consistencia en el frontend
            match_dict['winner_name'] = dm['winner_team_name']
            match_dict['loser_name'] = dm['loser_team_name']
            all_matches.append(match_dict)

        # Ordenar todos los partidos por fecha de forma descendente
        all_matches.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'), reverse=True)

        return jsonify(all_matches), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_player_history_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener historial: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_player_history_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener historial: {str(e)}"}), 500

# NUEVOS ENDPOINTS PARA EDITAR PARTIDOS
@app.route('/api/matches/<int:match_id>', methods=['GET'])
@login_required 
def get_match_details_api(match_id):
    db = get_db()
    try:
        match = db.execute(
            '''SELECT m.id, m.challenger_id, m.challenged_id, m.score_text, m.winner_id, m.loser_id, m.positions_swapped,
                      p_chal.first_name AS challenger_first_name, p_chal.last_name AS challenger_last_name,
                      p_chd.first_name AS challenged_first_name, p_chd.last_name AS challenged_last_name
               FROM Matches m
               JOIN Players p_chal ON m.challenger_id = p_chal.id
               JOIN Players p_chd ON m.challenged_id = p_chd.id
               WHERE m.id = ?''', (match_id,)
        ).fetchone()

        if not match:
            return jsonify({"error": "Partido no encontrado."}), 404

        match_dict = dict(match)
        sets_parsed = []
        if match_dict['score_text']:
            for s in match_dict['score_text'].split(', '):
                scores = s.split('-')
                if len(scores) == 2:
                    sets_parsed.append([int(scores[0]), int(scores[1])])
        match_dict['sets'] = sets_parsed

        match_dict['challenger_name'] = f"{match['challenger_first_name']} {match['challenger_last_name']}" 
        match_dict['challenged_name'] = f"{match['challenged_first_name']} {match['challenged_last_name']}"
        
        return jsonify(match_dict), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_match_details_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener detalles del partido: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_match_details_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener detalles del partido: {str(e)}"}), 500

@app.route('/api/matches/<int:match_id>/edit', methods=['POST'])
@login_required 
def edit_match_api(match_id):
    data = request.get_json()
    new_sets = data.get('sets')

    if not new_sets or not (2 <= len(new_sets) <= 3):
        return jsonify({"error": "Datos de sets incompletos o número de sets incorrecto para editar."}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        original_match = db.execute(
            'SELECT challenger_id, challenged_id, winner_id, loser_id, positions_swapped FROM Matches WHERE id = ?',
            (match_id,)
        ).fetchone()

        if not original_match:
            return jsonify({"error": "Partido original no encontrado."}), 404

        original_challenger_id = original_match['challenger_id']
        original_challenged_id = original_match['challenged_id']
        original_winner_id = original_match['winner_id']
        original_loser_id = original_match['loser_id']
        original_positions_swapped = original_match['positions_swapped']

        if original_positions_swapped:
            winner_original_pos = db.execute('SELECT initial_position FROM Players WHERE id = ?', (original_winner_id,)).fetchone()['initial_position']
            loser_original_pos = db.execute('SELECT initial_position FROM Players WHERE id = ?', (original_loser_id,)).fetchone()['initial_position']
            
            cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (winner_original_pos, original_winner_id))
            cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (loser_original_pos, original_loser_id))
            print(f"DEBUG: [edit_match_api] Posiciones originales revertidas para {original_winner_id} y {original_loser_id}.")

        new_chal_sets_won = sum(1 for s in new_sets if s[0] > s[1])
        new_chd_sets_won = len(new_sets) - new_chal_sets_won

        if not ((new_chal_sets_won == 2 and new_chd_sets_won < 2) or (new_chd_sets_won == 2 and new_chal_sets_won < 2)):
            return jsonify({"error": "Resultado de sets inválido: un jugador debe ganar 2 sets."}), 400

        new_score_text = ", ".join([f"{s[0]}-{s[1]}" for s in new_sets])
        new_challenger_won_match = new_chal_sets_won > new_chd_sets_won
        new_winner_id = original_challenger_id if new_challenger_won_match else original_challenged_id
        new_loser_id = original_challenged_id if new_challenger_won_match else original_challenger_id

        current_challenger_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (original_challenger_id,)).fetchone()['current_position']
        current_challenged_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (original_challenged_id,)).fetchone()['current_position']

        new_positions_swapped = False
        final_challenger_pos = current_challenger_pos
        final_challenged_pos = current_challenged_pos

        if new_challenger_won_match and current_challenger_pos > current_challenged_pos:
            final_challenger_pos, final_challenged_pos = current_challenged_pos, current_challenger_pos
            new_positions_swapped = True
            print(f"DEBUG: [edit_match_api] Intercambio de posiciones: {original_challenger_id} y {original_challenged_id}.")
        elif not new_challenger_won_match and current_challenged_pos > current_challenger_pos:
            pass

        cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (final_challenger_pos, original_challenger_id))
        cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (final_challenged_pos, original_challenged_id))
        print(f"DEBUG: [edit_match_api] Nuevas posiciones aplicadas: {original_challenger_id} a {final_challenger_pos}, {original_challenged_id} a {final_challenged_pos}.")

        cursor.execute(
            """UPDATE Matches SET score_text = ?, winner_id = ?, loser_id = ?, is_challenger_winner = ?, positions_swapped = ?
               WHERE id = ?""",
            (new_score_text, new_winner_id, new_loser_id, new_challenger_won_match, new_positions_swapped, match_id)
        )
        
        db.commit()
        print(f"DEBUG: [edit_match_api] Partido {match_id} editado exitosamente.")
        return jsonify({"message": "Partido editado exitosamente y posiciones actualizadas."}), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [edit_match_api] Error de SQLite: {str(e)}")
        db.rollback()
        return jsonify({"error": f"Error de base de datos al editar el partido: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [edit_match_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al editar el partido: {str(e)}"}), 500


# --- Punto de Entrada de la Aplicación ---
if __name__ == '__main__':
    with app.app_context():
        init_db()
        create_initial_admin() # Llama a la función para crear el admin
    app.run(debug=True)
