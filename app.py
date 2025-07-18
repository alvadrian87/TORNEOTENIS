import sqlite3
import os
import traceback
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, g, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import functools
from werkzeug.utils import secure_filename

print("--- APP.PY CARGADO Y EJECUTÁNDOSE - VERSIÓN: 2025-07-18_FINAL ---") # <<-- AÑADE ESTO

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
app.config['SECRET_KEY'] = 'os.environ.get('FLASK_SECRET_KEY')
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
        script_content = f.read()
        # print("DEBUG: Contenido del script SQL cargado.") # Descomenta para depurar
        # print(script_content[:500]) # Imprime los primeros 500 caracteres para verificar (temporal)
        db.cursor().executescript(script_content)
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

def get_active_tournament_id_by_type(tournament_type):
    db = get_db()
    # Debug: Mostrar qué tipo de torneo se está buscando
    print(f"DEBUG: get_active_tournament_id_by_type - Buscando torneo de tipo: '{tournament_type}'")

    # Primero, intentar encontrar un torneo activo
    tournament = db.execute(
        "SELECT id, name, is_active, type FROM Tournaments WHERE type = ? COLLATE NOCASE AND is_active = 1 ORDER BY start_date DESC LIMIT 1",
        (tournament_type,)
    ).fetchone()

    if tournament:
        print(f"DEBUG: get_active_tournament_id_by_type - Encontrado torneo ACTIVO: {tournament['name']} (ID: {tournament['id']})")
        return tournament['id']
    else:
        # Debug: Indicar que no se encontró activo, buscar el último
        print(f"DEBUG: get_active_tournament_id_by_type - No se encontró torneo ACTIVO para '{tournament_type}'.")
        # Si no hay un torneo activo, buscar el último torneo no activo del mismo tipo
        last_tournament = db.execute(
            """SELECT id, name, is_active, type FROM Tournaments
               WHERE type = ?
               ORDER BY end_date DESC, start_date DESC, created_at DESC LIMIT 1""",
            (tournament_type,)
        ).fetchone()

        if last_tournament:
            print(f"DEBUG: get_active_tournament_id_by_type - Usando el ÚLTIMO torneo encontrado: {last_tournament['name']} (ID: {last_tournament['id']}, Activo: {last_tournament['is_active']}).")
            return last_tournament['id']
        else:
            print(f"DEBUG: get_active_tournament_id_by_type - NO se encontró NINGÚN torneo de tipo '{tournament_type}', ni activo ni anterior.")
            return None
        

# --- Funciones de Ayuda para Archivos ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# --- Rutas de Páginas Web (Vistas) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/organizer')
@login_required
def organizer_page():
    # Asegúrate de que solo los administradores puedan acceder
    if not session.get('is_admin'):
        flash('Acceso denegado. No tienes permisos de organizador.', 'warning')
        return redirect(url_for('player_dashboard_page')) # Redirige al dashboard del jugador
    return send_from_directory(os.path.join(app.static_folder, 'organizer'), 'organizer.html')

@app.route('/all_matches')
@login_required
def all_matches_page():
    print("DEBUG: [all_matches_page] Accediendo a la página de todos los partidos.")
    return render_template('all_matches.html')

@app.route('/tournaments')
@login_required # Opcional: si quieres que sea visible sin login, quita esto y adapta la lógica JS
def tournaments_page():
    # Esta página listará todos los torneos disponibles, futuros, etc.
    return render_template('tournaments.html')

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


# En app.py, puedes agregar esta función auxiliar en cualquier lugar lógico,
# por ejemplo, después de las funciones de ayuda para DB (get_db, close_db, init_db, create_initial_admin)
# o antes de la sección de "API Endpoints".

@app.route('/api/obtener_todos_los_torneos_disponibles', methods=['GET']) # <<-- ¡NUEVA RUTA!
@login_required
def get_tournaments():
    print("DEBUG: ¡¡¡GET_TOURNAMENTS - NUEVA RUTA - CARGADA Y EJECUTADA!!!") # <<-- MENSAJE DISTINTIVO
    db = get_db()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Obtener el tiempo actual como objeto datetime para comparaciones
    current_datetime_obj = datetime.now()
    # Y también como string para comparaciones con strings de la DB si es necesario, o para output
    current_time_str = current_datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

    filter_status = request.args.get('status')
    filter_type = request.args.get('type')

    try:
        query = """
            SELECT
                t.id, t.name, t.description, t.start_date, t.end_date,
                t.registration_start_date, t.registration_end_date, t.type, t.category,
                t.max_slots, t.cost, t.requirements, t.location, t.status, t.is_published,
                t.organizer_id, t.created_at, t.rules_url,
                u.username AS organizer_username
            FROM Tournaments AS t
            JOIN Users AS u ON t.organizer_id = u.id
            WHERE 1=1
        """
        params = []

        if request.args.get('include_unpublished') == 'true':
            pass
        else:
            query += " AND t.is_published = 1"

        if filter_status:
            query += " AND t.status = ?"
            params.append(filter_status)

        if filter_type:
            query += " AND t.type = ?"
            params.append(filter_type)

        query += " ORDER BY t.start_date ASC"

        tournaments_db = db.execute(query, params).fetchall()

        tournaments_list = []
        player_id = session.get('player_id')

        for t in tournaments_db:
            is_registered = False
            if player_id:
                registered_check = db.execute(
                    "SELECT 1 FROM TournamentRegistrations WHERE player_id = ? AND tournament_id = ?",
                    (player_id, t['id'])
                ).fetchone()
                is_registered = registered_check is not None

            registration_status_text = ""
            can_register = False

            # Convertir fechas de la DB a objetos datetime de Python y manejar NULLs
            reg_start_obj = None
            if t['registration_start_date']:
                try:
                    reg_start_obj = datetime.strptime(t['registration_start_date'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"ADVERTENCIA: Formato de fecha de registro inicio inválido para torneo {t['id']}: {t['registration_start_date']}")
                    pass # Dejar como None si hay error de formato

            reg_end_obj = None
            if t['registration_end_date']:
                try:
                    reg_end_obj = datetime.strptime(t['registration_end_date'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"ADVERTENCIA: Formato de fecha de registro fin inválido para torneo {t['id']}: {t['registration_end_date']}")
                    pass # Dejar como None si hay error de formato


            if t['is_published'] == 0:
                registration_status_text = "No publicado"
                can_register = False
            elif reg_start_obj is None or reg_end_obj is None:
                 registration_status_text = "Fechas de registro no definidas"
                 can_register = False
            elif current_datetime_obj < reg_start_obj: # Comparar objetos datetime
                registration_status_text = "Registro abre " + reg_start_obj.strftime('%d/%m/%Y') # Formatear para el frontend
                can_register = False
            elif current_datetime_obj > reg_end_obj: # Comparar objetos datetime
                registration_status_text = "Registro cerrado"
                can_register = False
            else: # Registro actualmente abierto
                if t['max_slots'] is not None and t['max_slots'] > 0:
                    current_registrations = db.execute(
                        "SELECT COUNT(id) FROM TournamentRegistrations WHERE tournament_id = ? AND status = 'inscrito'",
                        (t['id'],)
                    ).fetchone()[0]
                    if current_registrations >= t['max_slots']:
                        registration_status_text = "Cupos llenos"
                        can_register = False
                    else:
                        registration_status_text = f"Inscripciones abiertas ({current_registrations}/{t['max_slots']} cupos)"
                        can_register = True
                else: # Inscripciones abiertas y sin límite de cupo (o max_slots es 0 o NULL)
                    registration_status_text = "Inscripciones abiertas"
                    can_register = True

            if is_registered:
                registration_status_text = "Ya inscrito"
                can_register = False

            tournaments_list.append({
                'id': t['id'],
                'name': t['name'],
                'description': t['description'],
                'start_date': t['start_date'], # Se mantienen como string YYYY-MM-DD
                'end_date': t['end_date'],     # Se mantienen como string YYYY-MM-DD
                'registration_start_date': t['registration_start_date'], # Se mantienen como string YYYY-MM-DD HH:MM:SS
                'registration_end_date': t['registration_end_date'],     # Se mantienen como string YYYY-MM-DD HH:MM:SS
                'type': t['type'],
                'category': t['category'],
                'max_slots': t['max_slots'],
                'cost': t['cost'],
                'requirements': t['requirements'],
                'location': t['location'],
                'status': t['status'],
                'is_published': t['is_published'],
                'organizer_id': t['organizer_id'],
                'organizer_name': t['organizer_username'],
                'created_at': t['created_at'],
                'rules_url': t['rules_url'],
                'is_registered': is_registered,
                'registration_info': registration_status_text,
                'can_register': can_register and player_id is not None
            })

        return jsonify(tournaments_list), 200

    except sqlite3.Error as e:
        print(f"ERROR DB en get_tournaments: {e}")
        return jsonify({"error": "Error de base de datos al obtener torneos."}), 500
    except Exception as e:
        print(f"ERROR GENERICO en get_tournaments: {e}")
        return jsonify({"error": "Error inesperado al obtener torneos."}), 500

def _recalculate_player_activity_status(player_id):
    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener TODOS los contadores separados por tipo de partido
        player = db.execute(
            '''SELECT 
                activity_index_single, challenges_emitted_single, challenges_accepted_single, challenges_won_single, defenses_successful_single,
                activity_index_doubles, challenges_emitted_doubles, challenges_accepted_doubles, challenges_won_doubles, defenses_successful_doubles,
                rejections_current_cycle, registration_type
            FROM Players WHERE id = ?''', 
            (player_id,)
        ).fetchone()

        if not player:
            print(f"ADVERTENCIA: Jugador con ID {player_id} no encontrado para recalcular estado de actividad.")
            return

        # --- Cálculo y Estado para INDIVIDUALES ---
        D_s = player['challenges_emitted_single']
        A_s = player['challenges_accepted_single']
        G_s = player['challenges_won_single']
        DF_s = player['defenses_successful_single']
        
        new_activity_index_single = D_s + (2 * A_s) + (3 * G_s) + DF_s
        
        new_status_single = 'rojo' # Default a rojo
        if new_activity_index_single >= 12:
            new_status_single = 'verde'
        elif new_activity_index_single >= 6 and new_activity_index_single <= 11:
            new_status_single = 'amarillo'
        
        # --- Cálculo y Estado para DOBLES ---
        D_d = player['challenges_emitted_doubles']
        A_d = player['challenges_accepted_doubles']
        G_d = player['challenges_won_doubles']
        DF_d = player['defenses_successful_doubles']
        
        new_activity_index_doubles = D_d + (2 * A_d) + (3 * G_d) + DF_d
        
        new_status_doubles = 'rojo' # Default a rojo
        if new_activity_index_doubles >= 12:
            new_status_doubles = 'verde'
        elif new_activity_index_doubles >= 6 and new_activity_index_doubles <= 11:
            new_status_doubles = 'amarillo'

        # --- Lógica de Estado GENERAL (combinado) y Rechazos ---
        # El estado general se basa en los estados individuales y de dobles, y los rechazos.
        new_general_status = 'rojo' # Por defecto, si no cumple nada, es rojo.
        
        # Si al menos una modalidad es verde, el general es al menos amarillo.
        if new_status_single == 'verde' or new_status_doubles == 'verde':
            new_general_status = 'verde'
        elif new_status_single == 'amarillo' or new_status_doubles == 'amarillo':
            new_general_status = 'amarillo'
        
        # Si tiene 2 o más rechazos en el ciclo actual, el estado general es 'rojo'
        if player['rejections_current_cycle'] >= 2:
            new_general_status = 'rojo'

        # Actualizar activity_index y activity_status en la base de datos
        cursor.execute(
            """UPDATE Players SET 
               activity_index_single = ?, activity_status_single = ?,
               activity_index_doubles = ?, activity_status_doubles = ?,
               activity_status = ?
               WHERE id = ?""", 
            (new_activity_index_single, new_status_single,
             new_activity_index_doubles, new_status_doubles,
             new_general_status, player_id,)
        )
        # db.commit() # No hacer commit aquí, se hace en la función que llama.
        print(f"DEBUG: Estado de actividad de Jugador {player_id} actualizado:")
        print(f"  Individual: Índice={new_activity_index_single}, Estado='{new_status_single}'")
        print(f"  Dobles: Índice={new_activity_index_doubles}, Estado='{new_status_doubles}'")
        print(f"  General: Estado='{new_general_status}' (Rechazos ciclo: {player['rejections_current_cycle']})")

    except sqlite3.Error as e:
        # db.rollback() # No hacer rollback aquí, se hace en la función que llama.
        print(f"ERROR DB: [_recalculate_player_activity_status] Error de SQLite: {str(e)}")
    except Exception as e:
        print(f"ERROR GENERICO: [_recalculate_player_activity_status] Error inesperado: {str(e)}")

def _recalculate_team_doubles_activity_status(team_id):
    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener los contadores de actividad del equipo de dobles
        team = db.execute(
            '''SELECT
                activity_index_team_doubles,
                challenges_emitted_team_doubles,
                challenges_accepted_team_doubles,
                challenges_won_team_doubles,
                defenses_successful_team_doubles,
                rejections_team_doubles_current_cycle
            FROM Teams WHERE id = ?''',
            (team_id,)
        ).fetchone()

        if not team:
            print(f"ADVERTENCIA: Equipo de dobles con ID {team_id} no encontrado para recalcular estado de actividad.")
            return

        # Calcular el nuevo índice de actividad para el equipo
        D_t = team['challenges_emitted_team_doubles']
        A_t = team['challenges_accepted_team_doubles']
        G_t = team['challenges_won_team_doubles']
        DF_t = team['defenses_successful_team_doubles']
        
        new_activity_index_team_doubles = D_t + (2 * A_t) + (3 * G_t) + DF_t
        
        # Determinar el estado de actividad del equipo (verde, amarillo, rojo)
        new_activity_status_team_doubles = 'rojo' # Default a rojo
        if new_activity_index_team_doubles >= 12: # Mismos umbrales que individuales por defecto
            new_activity_status_team_doubles = 'verde'
        elif new_activity_index_team_doubles >= 6 and new_activity_index_team_doubles <= 11:
            new_activity_status_team_doubles = 'amarillo'
        
        # Si tiene 2 o más rechazos en el ciclo actual, el estado del equipo es 'rojo'
        if team['rejections_team_doubles_current_cycle'] >= 2:
            new_activity_status_team_doubles = 'rojo'

        # Actualizar activity_index y activity_status en la base de datos para el equipo
        cursor.execute(
            """UPDATE Teams SET
               activity_index_team_doubles = ?,
               activity_status_team_doubles = ?
               WHERE id = ?""",
            (new_activity_index_team_doubles, new_activity_status_team_doubles, team_id,)
        )
        # NO HACER commit() o rollback() aquí. La función que llama manejará la transacción.
        print(f"DEBUG: Estado de actividad de Equipo {team_id} actualizado:")
        print(f"  Índice: {new_activity_index_team_doubles}, Estado: '{new_activity_status_team_doubles}'")
        print(f"  Rechazos ciclo: {team['rejections_team_doubles_current_cycle']}")

    except sqlite3.Error as e:
        print(f"ERROR DB: [_recalculate_team_doubles_activity_status] Error de SQLite: {str(e)}")
    except Exception as e:
        print(f"ERROR GENERICO: [_recalculate_team_doubles_activity_status] Error inesperado: {str(e)}")

def _recalculate_all_players_activity_status():
    db = get_db()
    players = db.execute('SELECT id FROM Players').fetchall()
    for player in players:
        _recalculate_player_activity_status(player['id'])
    # Importante: No hacer db.commit() aquí. El commit debe ser manejado por la función que llama
    # (e.g., reset_cycle_activity_api o cualquier otra que inicie un conjunto de recálculos).
    print("DEBUG: Recálculo de estado de actividad completado para todos los jugadores.")

# --- API Endpoints ---

@app.route('/api/players', methods=['GET'])
def get_players_api():
    db = get_db()
    players_db = db.execute(
        '''SELECT id, first_name, last_name, email, phone, gender,
                  birth_date, location, dominant_hand, backhand_type, racquet,
                  photo_url,
                  initial_position, current_position, points,
                  activity_index_single, challenges_emitted_single, challenges_accepted_single,
                  challenges_won_single, defenses_successful_single, activity_status_single,
                  activity_index_doubles, challenges_emitted_doubles, challenges_accepted_doubles,
                  challenges_won_doubles, defenses_successful_doubles, activity_status_doubles,
                  rejections_current_cycle, rejections_total, activity_status, last_activity_update,
                  last_challenge_received_date -- 'category' y 'registration_type' eliminados de aquí
           FROM Players ORDER BY current_position ASC'''
    ).fetchall()
    
    players = []
    for p in players_db:
        player_dict = dict(p)
        player_dict['name'] = f"{p['first_name']} {p['last_name']}"
        
        # Formatear last_activity_update para una mejor visualización si no es NULL
        if player_dict['last_activity_update']:
            try:
                # Asumiendo que se guarda como YYYY-MM-DD HH:MM:SS
                dt_object = datetime.strptime(player_dict['last_activity_update'], '%Y-%m-%d %H:%M:%S')
                player_dict['last_activity_update_formatted'] = dt_object.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                player_dict['last_activity_update_formatted'] = 'N/A' # O manejar como prefieras
        else:
            player_dict['last_activity_update_formatted'] = 'Nunca'

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
    
    # IMPORTANTE: Los IDs que vienen del frontend ahora son IDs de TEAMS GLOBALES
    # Necesitamos encontrar sus IDs de TournamentTeams para el torneo activo.
    challenger_team_id_global = data.get('challengerTeamId')
    challenged_team_id_global = data.get('challengedTeamId')

    if not all([challenger_team_id_global, challenged_team_id_global]):
        print("DEBUG: [propose_doubles_challenge_api] Faltan IDs de equipos globales.")
        return jsonify({"error": "Faltan IDs de equipos para proponer el desafío."}), 400
    
    if int(challenger_team_id_global) == int(challenged_team_id_global):
        return jsonify({"error": "Un equipo no puede desafiarse a sí mismo."}), 400

    db = get_db()
    cursor = db.cursor()
    inserted_id = None 

    try:
        # Primero, obtener los equipos globales y su género
        challenger_team_global_info = db.execute('SELECT id, gender_category FROM Teams WHERE id = ?', (challenger_team_id_global,)).fetchone()
        challenged_team_global_info = db.execute('SELECT id, gender_category FROM Teams WHERE id = ?', (challenged_team_id_global,)).fetchone()

        if not challenger_team_global_info or not challenged_team_global_info:
            return jsonify({"error": "Uno o ambos equipos globales no encontrados."}), 404
        
        if challenger_team_global_info['gender_category'] != challenged_team_global_info['gender_category']:
            return jsonify({"error": "Los equipos deben ser del mismo género."}), 400

        gender_category = challenger_team_global_info['gender_category']
        # Corregir la construcción del tipo de torneo para que coincida con schema.sql
        if gender_category == 'Masculino':
            tournament_type = 'pyramid_doubles_male'
        elif gender_category == 'Femenino':
            tournament_type = 'pyramid_doubles_female' # <-- CORRECCIÓN AQUÍ
        else:
            tournament_type = f"pyramid_doubles_{gender_category.lower()}" # Fallback, aunque solo esperamos Masculino/Femenino


        # --- NUEVA LÓGICA: Obtener el ID del torneo de dobles pirámide activo ---
        active_tournament_id = get_active_tournament_id_by_type(tournament_type)
        if not active_tournament_id:
            return jsonify({"error": f"No hay un torneo de pirámide de dobles {gender_category} activo para proponer desafíos."}), 400
        # --- FIN NUEVA LÓGICA ---

        # Obtener los IDs de TournamentTeams para el torneo activo
        challenger_tournament_team = db.execute(
            'SELECT id, tournament_current_position FROM TournamentTeams WHERE tournament_id = ? AND team_id = ?',
            (active_tournament_id, challenger_team_id_global)
        ).fetchone()
        challenged_tournament_team = db.execute(
            'SELECT id, tournament_current_position FROM TournamentTeams WHERE tournament_id = ? AND team_id = ?',
            (active_tournament_id, challenged_team_id_global)
        ).fetchone()

        if not challenger_tournament_team or not challenged_tournament_team:
            return jsonify({"error": "Uno o ambos equipos no están registrados en el torneo de dobles activo."}), 400
        
        # Ahora trabajamos con los IDs de TournamentTeams
        challenger_tournament_team_id = challenger_tournament_team['id']
        challenged_tournament_team_id = challenged_tournament_team['id']

        # Reglas de desafío (aplicadas a posiciones de TournamentTeams)
        challenger_pos = challenger_tournament_team['tournament_current_position']
        challenged_pos = challenged_tournament_team['tournament_current_position']
        
        # Obtener el total de equipos en TournamentTeams para la categoría de género del desafiante y el torneo activo
        total_teams_in_category = db.execute(
            '''SELECT COUNT(tt.id) FROM TournamentTeams tt
               JOIN Teams t ON tt.team_id = t.id
               WHERE tt.tournament_id = ? AND t.gender_category = ?''',
            (active_tournament_id, gender_category)
        ).fetchone()[0]

        is_valid_challenge_rule = False
        validation_message = "Desafío de dobles no permitido."

        if challenger_pos == 1: # Puesto 1
            if challenged_pos >= 2 and challenged_pos <= 6:
                is_valid_challenge_rule = True
                validation_message = "Desafío permitido: Puesto 1 puede desafiar a 2-6."
            else:
                validation_message = "Puesto 1 solo puede desafiar a equipos entre el puesto 2 y 6."
        elif challenger_pos == 2: # Puesto 2
            if challenged_pos in [1, 3, 4]:
                is_valid = True
                validation_message = "Desafío permitido: Puesto 2 puede desafiar a 1, 3 y 4."
            else:
                validation_message = "Puesto 2 solo puede desafiar a equipos en los puestos 1, 3 y 4."
        elif challenger_pos == 3: # Puesto 3
            if challenged_pos in [1, 2, 4]:
                is_valid = True
                validation_message = "Desafío permitido: Puesto 3 puede desafiar a 1, 2 y 4."
            else:
                validation_message = "Puesto 3 solo puede desafiar a equipos en los puestos 1, 2 y 4."
        elif challenger_pos == total_teams_in_category: # Último equipo en su categoría
            if challenged_pos >= (total_teams_in_category - 5) and challenged_pos < total_teams_in_category: # Los 5 de arriba
                is_valid_challenge_rule = True
                validation_message = "Desafío permitido: Último equipo puede desafiar a los 5 de arriba."
            else:
                validation_message = "El último equipo solo puede desafiar a los 5 equipos inmediatamente superiores."
        elif challenger_pos >= 4: # Puesto 4 en adelante (no el último)
            # Puede desafiar a los 3 equipos inmediatamente por encima
            if challenged_pos >= (challenger_pos - 3) and challenged_pos < challenger_pos:
                is_valid_challenge_rule = True
                validation_message = "Desafío permitido: Puede desafiar a los 3 equipos inmediatamente superiores."
            else:
                validation_message = "Solo puedes desafiar a los 3 equipos inmediatamente superiores."
        
        # Si la regla de desafío no es válida, devolver error.
        if not is_valid_challenge_rule:
            return jsonify({"error": validation_message}), 400

        # Verificar si ya existe un desafío pendiente entre estos dos TournamentTeams para este torneo
        existing_challenge = db.execute(
            '''SELECT id FROM DoublesMatches 
               WHERE tournament_id = ? 
                 AND ((team_a_id = ? AND team_b_id = ?) OR (team_a_id = ? AND team_b_id = ?))
                 AND status = 'pending' ''',
            (active_tournament_id, challenger_tournament_team_id, challenged_tournament_team_id, 
             challenged_tournament_team_id, challenger_tournament_team_id)
        ).fetchone()

        if existing_challenge:
            print(f"DEBUG: [propose_doubles_challenge_api] Desafío de dobles ya existe (ID: {existing_challenge['id']}).")
            return jsonify({"error": "Ya existe un desafío de dobles pendiente entre estos equipos."}), 409

        # Si todas las validaciones pasan, insertar el desafío.
        cursor.execute(
            """INSERT INTO DoublesMatches (tournament_id, team_a_id, team_b_id, status)
               VALUES (?, ?, ?, ?)""",
            (active_tournament_id, challenger_tournament_team_id, challenged_tournament_team_id, 'pending')
        )
        inserted_id = cursor.lastrowid
        print(f"DEBUG: [propose_doubles_challenge_api] Intentando COMMIT para challenge_id: {inserted_id}")
        
        # --- LÓGICA DE ACTIVIDAD PARA EQUIPOS DE DOBLES (AHORA EN TournamentTeams) ---
        # Incrementar challenges_emitted_team_doubles para el TournamentTeam desafiante
        cursor.execute(
            """UPDATE TournamentTeams SET
               challenges_emitted_team_doubles = challenges_emitted_team_doubles + 1,
               last_activity_team_doubles_update = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (challenger_tournament_team_id,)
        )
        # Recalcular el estado de actividad del TournamentTeam desafiante
        _recalculate_team_doubles_activity_status(challenger_tournament_team_id)
        # --- FIN NUEVA LÓGICA ---

        db.commit()
        print(f"DEBUG: [propose_doubles_challenge_api] COMMIT EXITOSO para challenge_id: {inserted_id}")
        return jsonify({"message": "Desafío de dobles propuesto y registrado como pendiente.", "challenge_id": inserted_id}), 201

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [propose_doubles_challenge_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al proponer desafío de dobles: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [propose_doubles_challenge_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al proponer desafío de dobles: {str(e)}"}), 500


@app.route('/api/doubles_teams', methods=['GET'])
def get_doubles_teams_api():
    db = get_db()
    gender_filter = request.args.get('gender') # 'Masculino' o 'Femenino'

    # 1. Identificar el Torneo Pirámide de Dobles activo para el género solicitado
    active_pyramid_tournament = None
    tournament_type_search = None # Usar una variable diferente para la búsqueda
    if gender_filter == 'Masculino':
        tournament_type_search = 'pyramid_doubles_male'
    elif gender_filter == 'Femenino':
        tournament_type_search = 'pyramid_doubles_female' # ESTA CADENA DEBE COINCIDIR CON SCHEMA.SQL

    if tournament_type_search: # Solo buscar si se especificó un tipo de torneo válido
        # Usar COLLATE NOCASE para que la búsqueda de tipo sea insensible a mayúsculas/minúsculas
        active_pyramid_tournament = db.execute(
            "SELECT id FROM Tournaments WHERE is_active = 1 AND type = ? COLLATE NOCASE",
            (tournament_type_search,) # Usar la variable de búsqueda
        ).fetchone()
        
        # Si no hay activo, buscar el último jugado/creado
        if not active_pyramid_tournament:
            active_pyramid_tournament = db.execute(
                """SELECT id FROM Tournaments
                   WHERE type = ? COLLATE NOCASE
                   ORDER BY end_date DESC, start_date DESC, created_at DESC LIMIT 1""",
                (tournament_type_search,) # Usar la variable de búsqueda
            ).fetchone()

    if not active_pyramid_tournament:
        # Este es el mensaje que está recibiendo el frontend si no se encuentra el torneo
        return jsonify({"message": f"No hay un torneo de dobles {gender_filter if gender_filter else 'Femenino'} disponible (ni activo ni anterior)."}), 404
    
    tournament_id = active_pyramid_tournament['id']

    # 2. Construir la consulta para obtener los equipos del TournamentTeams activo
    query = '''
        SELECT tt.tournament_current_position AS current_position,
               tt.tournament_initial_position AS initial_position,
               tt.tournament_points AS points,
               tt.activity_index_team_doubles,
               tt.challenges_emitted_team_doubles,
               tt.challenges_accepted_team_doubles,
               tt.challenges_won_team_doubles,
               tt.defenses_successful_team_doubles,
               tt.rejections_team_doubles_current_cycle,
               tt.rejections_team_doubles_total,
               tt.activity_status_team_doubles,
               tt.last_activity_team_doubles_update,
               t.id AS team_id,
               t.team_name,
               t.player1_id,
               t.player2_id,
               t.gender_category,
               p1.first_name AS p1_first_name, p1.last_name AS p1_last_name,
               p2.first_name AS p2_first_name, p2.last_name AS p2_last_name
        FROM TournamentTeams tt
        JOIN Teams t ON tt.team_id = t.id
        JOIN Players p1 ON t.player1_id = p1.id
        JOIN Players p2 ON t.player2_id = p2.id
        WHERE tt.tournament_id = ?
    '''
    params = [tournament_id]

    if gender_filter:
        query += ' AND t.gender_category = ?'
        params.append(gender_filter)
    
    query += ' ORDER BY tt.tournament_current_position ASC'

    try:
        teams_db = db.execute(query, params).fetchall()
        teams = []
        for t in teams_db:
            team_dict = dict(t)
            team_dict['player1_name'] = f"{t['p1_first_name']} {t['p1_last_name']}"
            team_dict['player2_name'] = f"{t['p2_first_name']} {t['p2_last_name']}"
            
            if team_dict['last_activity_team_doubles_update']:
                try:
                    dt_object = datetime.strptime(team_dict['last_activity_team_doubles_update'], '%Y-%m-%d %H:%M:%S')
                    team_dict['last_activity_team_doubles_update_formatted'] = dt_object.strftime('%d/%m/%Y %H:%M')
                except ValueError:
                    team_dict['last_activity_team_doubles_update_formatted'] = 'N/A'
            else:
                team_dict['last_activity_team_doubles_update_formatted'] = 'Nunca'

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
    # Los IDs que vienen son IDs de TEAMS GLOBALES
    challenger_team_id_global = data.get('challengerTeamId')
    challenged_team_id_global = data.get('challengedTeamId')

    if not all([challenger_team_id_global, challenged_team_id_global]):
        return jsonify({"error": "Faltan IDs de equipos."}), 400

    db = get_db()
    
    # Obtener el género de los equipos globales para identificar el tipo de torneo
    challenger_team_global_info = db.execute('SELECT id, gender_category FROM Teams WHERE id = ?', (challenger_team_id_global,)).fetchone()
    challenged_team_global_info = db.execute('SELECT id, gender_category FROM Teams WHERE id = ?', (challenged_team_id_global,)).fetchone()

    if not challenger_team_global_info or not challenged_team_global_info:
        return jsonify({"error": "Uno o ambos equipos globales no encontrados."}), 404
    
    if challenger_team_global_info['gender_category'] != challenged_team_global_info['gender_category']:
        return jsonify({"error": "Los equipos deben ser del mismo género."}), 400

    gender_category = challenger_team_global_info['gender_category']
    # Corregir la construcción del tipo de torneo para que coincida con schema.sql
    if gender_category == 'Masculino':
        tournament_type = 'pyramid_doubles_male'
    elif gender_category == 'Femenino':
        tournament_type = 'pyramid_doubles_female' # <-- CORRECCIÓN AQUÍ
    else:
        tournament_type = f"pyramid_doubles_{gender_category.lower()}"

    # --- NUEVA LÓGICA: Verificar torneo activo para la validación ---
    active_tournament_id = get_active_tournament_id_by_type(tournament_type)
    if not active_tournament_id:
        return jsonify({"valid": False, "message": f"No hay un torneo de pirámide de dobles {gender_category} activo para validar desafíos."}), 400
    # --- FIN NUEVA LÓGICA ---

    # Obtener las posiciones de los equipos de TournamentTeams para el torneo activo
    challenger_tournament_team = db.execute(
        'SELECT id, tournament_current_position FROM TournamentTeams WHERE tournament_id = ? AND team_id = ?',
        (active_tournament_id, challenger_team_id_global)
    ).fetchone()
    challenged_tournament_team = db.execute(
        'SELECT id, tournament_current_position FROM TournamentTeams WHERE tournament_id = ? AND team_id = ?',
        (active_tournament_id, challenged_team_id_global)
    ).fetchone()

    if not challenger_tournament_team or not challenged_tournament_team:
        return jsonify({"valid": False, "message": "Uno o ambos equipos no están registrados en el torneo de dobles activo."}), 400

    challenger_pos = challenger_tournament_team['tournament_current_position']
    challenged_pos = challenged_tournament_team['tournament_current_position']
    
    # Obtener el total de equipos en TournamentTeams para la categoría de género y el torneo activo
    total_teams_in_category = db.execute(
        '''SELECT COUNT(tt.id) FROM TournamentTeams tt
           JOIN Teams t ON tt.team_id = t.id
           WHERE tt.tournament_id = ? AND t.gender_category = ?''', 
        (active_tournament_id, gender_category)
    ).fetchone()[0]

    is_valid = False
    message = "Desafío de dobles no permitido."

    # Reglas de desafío (aplicadas a posiciones de TournamentTeams)
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
        query = '''
            SELECT dc.id, dc.date, dc.team_a_id, dc.team_b_id, dc.status, dc.created_at,
                   t_a.team_name AS challenger_team_name, t_b.team_name AS challenged_team_name
            FROM DoublesMatches dc
            JOIN Teams t_a ON dc.team_a_id = t_a.id
            JOIN Teams t_b ON dc.team_b_id = t_b.id
            WHERE dc.status = 'pending'
            ORDER BY dc.created_at DESC
        '''
        print(f"DEBUG: [get_pending_doubles_challenges_api] Consulta SQL: {query}") # NUEVO DEBUG
        
        pending_doubles_challenges_db = db.execute(query).fetchall()

        challenges = []
        for pc in pending_doubles_challenges_db:
            challenge_dict = dict(pc)
            challenge_dict['challenger_team_id'] = pc['team_a_id']
            challenge_dict['challenged_team_id'] = pc['team_b_id']
            challenge_dict['challenger_team_name'] = pc['challenger_team_name']
            challenge_dict['challenged_team_name'] = pc['challenged_team_name']
            challenges.append(challenge_dict)

        print(f"DEBUG: [get_pending_doubles_challenges_api] Desafíos encontrados en DB: {challenges}") # NUEVO DEBUG
        return jsonify(challenges), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_pending_doubles_challenges_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener desafíos de dobles pendientes: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_pending_doubles_challenges_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener desafíos de dobles pendientes: {str(e)}"}), 500

# En app.py, dentro de la sección de "API Endpoints"

@app.route('/api/doubles_match_result', methods=['POST'])
@login_required 
def post_doubles_match_result_api():
    data = request.get_json()
    # Los IDs que vienen del frontend ahora son IDs de TEAMS GLOBALES
    challenger_team_id_global = int(data.get('challengerTeamId'))
    challenged_team_id_global = int(data.get('challengedTeamId'))
    sets = data.get('sets')
    challenge_id = data.get('challengeId') # ID del desafío pendiente, si viene de uno

    print(f"DEBUG: [post_doubles_match_result_api] Datos recibidos: {data}")
    print(f"DEBUG: [post_doubles_match_result_api] Challenge ID recibido: {challenge_id}")

    if not all([challenger_team_id_global, challenged_team_id_global, sets]) or not (2 <= len(sets) <= 3):
        return jsonify({"error": "Datos de partido de dobles incompletos o número de sets incorrecto."}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener los equipos globales y su género
        challenger_team_global_info = db.execute('SELECT id, gender_category, player1_id, player2_id FROM Teams WHERE id = ?', (challenger_team_id_global,)).fetchone()
        challenged_team_global_info = db.execute('SELECT id, gender_category, player1_id, player2_id FROM Teams WHERE id = ?', (challenged_team_id_global,)).fetchone()

        if not challenger_team_global_info or not challenged_team_global_info:
            return jsonify({"error": "Uno o ambos equipos globales no encontrados."}), 404

        gender_category = challenger_team_global_info['gender_category']
        # Corregir la construcción del tipo de torneo para que coincida con schema.sql
        if gender_category == 'Masculino':
            tournament_type = 'pyramid_doubles_male'
        elif gender_category == 'Femenino':
            tournament_type = 'pyramid_doubles_female' # <-- CORRECCIÓN AQUÍ
        else:
            tournament_type = f"pyramid_doubles_{gender_category.lower()}"

        # --- NUEVA LÓGICA: Obtener el ID del torneo de dobles pirámide activo ---
        active_tournament_id = get_active_tournament_id_by_type(tournament_type)
        if not active_tournament_id:
            return jsonify({"error": f"No hay un torneo de pirámide de dobles {gender_category} activo para registrar resultados."}), 400
        # --- FIN NUEVA LÓGICA ---

        # Obtener los IDs de TournamentTeams y sus posiciones para el torneo activo
        challenger_tournament_team = db.execute(
            'SELECT id, tournament_current_position, team_id FROM TournamentTeams WHERE tournament_id = ? AND team_id = ?',
            (active_tournament_id, challenger_team_id_global)
        ).fetchone()
        challenged_tournament_team = db.execute(
            'SELECT id, tournament_current_position, team_id FROM TournamentTeams WHERE tournament_id = ? AND team_id = ?',
            (active_tournament_id, challenged_team_id_global)
        ).fetchone()

        if not challenger_tournament_team or not challenged_tournament_team:
            return jsonify({"error": "Uno o ambos equipos no están registrados en el torneo de dobles activo."}), 400
        
        # Usar los IDs de TournamentTeams para todas las operaciones subsiguientes
        challenger_tournament_team_id = challenger_tournament_team['id']
        challenged_tournament_team_id = challenged_tournament_team['id']
        
        # Obtener info de torneo para lógica condicional (pyramid vs satellite)
        tournament_info = db.execute("SELECT type FROM Tournaments WHERE id = ?", (active_tournament_id,)).fetchone()
        if not tournament_info:
            return jsonify({"error": "Información del torneo activo no encontrada."}), 500 # Esto no debería pasar

        is_pyramid_doubles_tournament = tournament_info['type'].startswith('pyramid_doubles_')


        chal_sets_won = sum(1 for s in sets if s[0] > s[1])
        chd_sets_won = len(sets) - chal_sets_won
        
        if not ((chal_sets_won == 2 and chd_sets_won < 2) or (chd_sets_won == 2 and chal_sets_won < 2)):
            return jsonify({"error": "Resultado inválido para dobles: un equipo debe ganar 2 sets."}), 400

        score_text = ", ".join([f"{s[0]}-{s[1]}" for s in sets])
        
        challenger_won_match = chal_sets_won > chd_sets_won # Si el equipo A (challenger) ganó el partido
        winner_tournament_team_id = challenger_tournament_team_id if challenger_won_match else challenged_tournament_team_id
        loser_tournament_team_id = challenged_tournament_team_id if challenger_won_match else challenger_tournament_team_id

        positions_swapped = False
        new_challenger_team_pos, new_challenged_team_pos = challenger_tournament_team['tournament_current_position'], challenged_tournament_team['tournament_current_position']

        # Lógica de actualización de posiciones y actividad SOLO si es un torneo pirámide de dobles
        if is_pyramid_doubles_tournament:
            # Lógica de intercambio de posiciones para dobles (ahora sobre TournamentTeams)
            if challenger_won_match and challenger_tournament_team['tournament_current_position'] > challenged_tournament_team['tournament_current_position']:
                new_challenger_team_pos = challenged_tournament_team['tournament_current_position']
                new_challenged_team_pos = challenger_tournament_team['tournament_current_position']
                positions_swapped = True
                print(f"DEBUG: Standard swap (Doubles) - Challenger TournamentTeam {challenger_tournament_team_id} won against {challenged_tournament_team_id}. Positions swapped.")

            elif not challenger_won_match and challenger_tournament_team['tournament_current_position'] == 1:
                new_challenger_team_pos = challenged_tournament_team['tournament_current_position']
                new_challenged_team_pos = challenger_tournament_team['tournament_current_position']
                positions_swapped = True
                print(f"DEBUG: Puesto 1 lost (Doubles) - Challenger TournamentTeam {challenger_tournament_team_id} (P1) lost to {challenged_tournament_team_id}. Positions swapped.")
            
            # Actualizar posiciones de los TournamentTeams
            cursor.execute("UPDATE TournamentTeams SET tournament_current_position = ? WHERE id = ?", (new_challenger_team_pos, challenger_tournament_team_id))
            cursor.execute("UPDATE TournamentTeams SET tournament_current_position = ? WHERE id = ?", (new_challenged_team_pos, challenged_tournament_team_id))
            
            # --- LÓGICA DE ACTIVIDAD PARA JUGADORES INDIVIDUALES (RANKING MAESTRO) ---
            # OJO: Estos IDs son de la tabla Players global, no de TournamentPlayers.
            player1_challenger_id = challenger_team_global_info['player1_id']
            player2_challenger_id = challenger_team_global_info['player2_id']
            player1_challenged_id = challenged_team_global_info['player1_id']
            player2_challenged_id = challenged_team_global_info['player2_id']

            # Actualizar contadores de actividad para los jugadores del equipo desafiante (Ranking Maestro)
            cursor.execute("UPDATE Players SET challenges_emitted_doubles = challenges_emitted_doubles + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (player1_challenger_id,))
            cursor.execute("UPDATE Players SET challenges_emitted_doubles = challenges_emitted_doubles + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (player2_challenger_id,))
            
            # Actualizar contadores de actividad para los jugadores del equipo desafiado (Ranking Maestro)
            cursor.execute("UPDATE Players SET challenges_accepted_doubles = challenges_accepted_doubles + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (player1_challenged_id,))
            cursor.execute("UPDATE Players SET challenges_accepted_doubles = challenges_accepted_doubles + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (player2_challenged_id,))

            # Actualizar contadores de actividad para los jugadores del equipo ganador y perdedor (Ranking Maestro)
            if challenger_won_match: # Equipo desafiante ganó
                cursor.execute("UPDATE Players SET challenges_won_doubles = challenges_won_doubles + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (player1_challenger_id,))
                cursor.execute("UPDATE Players SET challenges_won_doubles = challenges_won_doubles + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (player2_challenger_id,))
            else: # Equipo desafiado ganó (defensa exitosa)
                cursor.execute("UPDATE Players SET defenses_successful_doubles = defenses_successful_doubles + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (player1_challenged_id,))
                cursor.execute("UPDATE Players SET defenses_successful_doubles = defenses_successful_doubles + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (player2_challenged_id,))
            
            # --- LLAMADA A LA FUNCIÓN DE RECÁLCULO DE ESTADO DE JUGADORES ---
            _recalculate_player_activity_status(player1_challenger_id)
            _recalculate_player_activity_status(player2_challenger_id)
            _recalculate_player_activity_status(player1_challenged_id)
            _recalculate_player_activity_status(player2_challenged_id)
            # --- FIN LLAMADA ---

        else:
            print(f"DEBUG: Partido de dobles en torneo tipo '{tournament_info['type']}' no afecta Ranking Maestro ni actividad de jugadores globales.")
            
        # --- LÓGICA DE ACTIVIDAD PARA EQUIPOS DE DOBLES (TournamentTeams) ---
        # Actualizar contadores de actividad para el TournamentTeam desafiante (siempre)
        cursor.execute(
            """UPDATE TournamentTeams SET 
               challenges_emitted_team_doubles = challenges_emitted_team_doubles + 1, 
               last_activity_team_doubles_update = CURRENT_TIMESTAMP 
               WHERE id = ?""", 
            (challenger_tournament_team_id,)
        )
        # Actualizar contadores de actividad para el TournamentTeam desafiado (siempre)
        cursor.execute(
            """UPDATE TournamentTeams SET 
               challenges_accepted_team_doubles = challenges_accepted_team_doubles + 1, 
               last_activity_team_doubles_update = CURRENT_TIMESTAMP 
               WHERE id = ?""", 
            (challenged_tournament_team_id,)
        )

        # Actualizar contadores de actividad para el TournamentTeam ganador y perdedor (siempre)
        if challenger_won_match: # Equipo desafiante ganó
            cursor.execute(
                """UPDATE TournamentTeams SET 
                   challenges_won_team_doubles = challenges_won_team_doubles + 1, 
                   last_activity_team_doubles_update = CURRENT_TIMESTAMP 
                   WHERE id = ?""", 
                (challenger_tournament_team_id,)
            )
        else: # Equipo desafiado ganó (defensa exitosa)
            cursor.execute(
                """UPDATE TournamentTeams SET 
                   defenses_successful_team_doubles = defenses_successful_team_doubles + 1, 
                   last_activity_team_doubles_update = CURRENT_TIMESTAMP 
                   WHERE id = ?""", 
                (challenged_tournament_team_id,)
            )
        
        # --- LLAMADA A LA FUNCIÓN DE RECÁLCULO DE ESTADO DE EQUIPOS ---
        _recalculate_team_doubles_activity_status(challenger_tournament_team_id)
        _recalculate_team_doubles_activity_status(challenged_tournament_team_id)
        # --- FIN LLAMADA ---

        doubles_match_id = None 

        if challenge_id:
            cursor.execute(
                """UPDATE DoublesMatches SET date = ?, winner_team_id = ?, loser_team_id = ?, score_text = ?, is_team_a_winner = ?, positions_swapped = ?, status = 'played'
                   WHERE id = ?""",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), winner_tournament_team_id, loser_tournament_team_id, score_text, challenger_won_match, positions_swapped, challenge_id)
            )
            doubles_match_id = challenge_id
            print(f"DEBUG: [post_doubles_match_result_api] Desafío pendiente {challenge_id} actualizado a 'played'. Filas afectadas: {cursor.rowcount}")
            if cursor.rowcount == 0:
                print(f"ADVERTENCIA: [post_doubles_match_result_api] No se encontró el desafío de dobles con ID {challenge_id} para actualizar. Podría no existir o ya no estar pendiente.")
        else:
            cursor.execute(
                """INSERT INTO DoublesMatches (tournament_id, date, team_a_id, team_b_id, winner_team_id, loser_team_id, score_text, is_team_a_winner, positions_swapped, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (active_tournament_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), challenger_tournament_team_id, challenged_tournament_team_id, winner_tournament_team_id, loser_tournament_team_id, score_text, challenger_won_match, positions_swapped, 'played')
            )
            doubles_match_id = cursor.lastrowid
            print(f"DEBUG: [post_doubles_match_result_api] Nuevo partido de dobles insertado (sin desafío pendiente previo). ID: {doubles_match_id}")
        
        # Registrar eventos en ActivityLog para los jugadores individuales (Ranking Maestro)
        if doubles_match_id:
            # Obtener los IDs de los jugadores globales para el ActivityLog (porque el log es para Players)
            player1_challenger_id_global = challenger_team_global_info['player1_id']
            player2_challenger_id_global = challenger_team_global_info['player2_id']
            player1_challenged_id_global = challenged_team_global_info['player1_id']
            player2_challenged_id_global = challenged_team_global_info['player2_id']

            cursor.execute(
                """INSERT INTO ActivityLog (player_id, event_type, doubles_match_id, tournament_id, details)
                   VALUES (?, ?, ?, ?, ?)""",
                (player1_challenger_id_global, 'doubles_match_played', doubles_match_id, active_tournament_id, f"Jugó dobles contra Equipo {challenged_team_id_global} en torneo {active_tournament_id}")
            )
            cursor.execute(
                """INSERT INTO ActivityLog (player_id, event_type, doubles_match_id, tournament_id, details)
                   VALUES (?, ?, ?, ?, ?)""",
                (player2_challenger_id_global, 'doubles_match_played', doubles_match_id, active_tournament_id, f"Jugó dobles contra Equipo {challenged_team_id_global} en torneo {active_tournament_id}")
            )
            cursor.execute(
                """INSERT INTO ActivityLog (player_id, event_type, doubles_match_id, tournament_id, details)
                   VALUES (?, ?, ?, ?, ?)""",
                (player1_challenged_id_global, 'doubles_match_played', doubles_match_id, active_tournament_id, f"Jugó dobles contra Equipo {challenger_team_id_global} en torneo {active_tournament_id}")
            )
            cursor.execute(
                """INSERT INTO ActivityLog (player_id, event_type, doubles_match_id, tournament_id, details)
                   VALUES (?, ?, ?, ?, ?)""",
                (player2_challenged_id_global, 'doubles_match_played', doubles_match_id, active_tournament_id, f"Jugó dobles contra Equipo {challenger_team_id_global} en torneo {active_tournament_id}")
            )
        
        db.commit()
        
        g.pop('db', None)
        db.close()
        return jsonify({"message": "Resultado de dobles procesado exitosamente y posiciones actualizadas."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [post_doubles_match_result_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al procesar resultado de dobles: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [post_doubles_match_result_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al procesar resultado de dobles: {str(e)}"}), 500        
    

@app.route('/api/all_matches', methods=['GET'])
@login_required # Proteger este endpoint si solo el organizador debe ver todos los partidos
def get_all_matches_api():
    db = get_db()
    try:
        # --- NUEVA LÓGICA: Obtener el ID del torneo pirámide individual activo ---
        active_tournament_id = get_active_tournament_id_by_type('pyramid_single')
        if not active_tournament_id:
            return jsonify({"message": "No hay un torneo de pirámide individual activo para listar partidos."}), 404
        # --- FIN NUEVA LÓGICA ---

        matches_db = db.execute(
            '''SELECT m.id, m.date, m.score_text,
                      p_chal.first_name AS challenger_first_name, p_chal.last_name AS challenger_last_name,
                      p_chd.first_name AS challenged_first_name, p_chd.last_name AS challenged_last_name,
                      p_winner.first_name AS winner_first_name, p_winner.last_name AS winner_last_name,
                      p_loser.first_name AS loser_first_name, p_loser.last_name AS loser_last_name,
                      t.name AS tournament_name, -- AÑADIR: Nombre del torneo
                      'single' AS match_type
               FROM Matches m
               JOIN Players p_chal ON m.challenger_id = p_chal.id
               JOIN Players p_chd ON m.challenged_id = p_chd.id
               JOIN Players p_winner ON m.winner_id = p_winner.id
               JOIN Players p_loser ON m.loser_id = p_loser.id
               JOIN Tournaments t ON m.tournament_id = t.id -- NUEVO: Unir con Tournaments
               WHERE m.tournament_id = ? -- NUEVO: Filtrar por el torneo activo
               ORDER BY m.date DESC''',
            (active_tournament_id,) # Pasar el ID del torneo activo
        ).fetchall()

        matches = []
        for m in matches_db:
            match_dict = dict(m)
            match_dict['challenger_name'] = f"{m['challenger_first_name']} {m['challenger_last_name']}"
            match_dict['challenged_name'] = f"{m['challenged_first_name']} {m['challenged_last_name']}"
            match_dict['winner_name'] = f"{m['winner_first_name']} {m['winner_last_name']}"
            match_dict['loser_name'] = f"{m['loser_first_name']} {m['loser_last_name']}"
            # El nombre del torneo ya viene en match_dict['tournament_name']
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
    gender_filter = request.args.get('gender') # Puede filtrar por género (ej. ?gender=Masculino)
    
    # --- NUEVA LÓGICA: Obtener el ID del torneo pirámide de dobles activo ---
    active_tournament_id = None
    tournament_type_search = None
    if gender_filter == 'Masculino':
        tournament_type_search = 'pyramid_doubles_male'
    elif gender_filter == 'Femenino':
        tournament_type_search = 'pyramid_doubles_female' # ESTA CADENA DEBE COINCIDIR CON SCHEMA.SQL
    
    if tournament_type_search:
        active_tournament_id = get_active_tournament_id_by_type(tournament_type_search)

    if not active_tournament_id:
        # Este es el mensaje que está recibiendo el frontend si no se encuentra el torneo
        return jsonify({"message": f"No hay un torneo de dobles {gender_filter if gender_filter else 'activo'} para listar partidos."}), 404
    # --- FIN NUEVA LÓGICA ---

    try:
        doubles_matches_db = db.execute(
            '''SELECT dm.id, dm.date, dm.score_text,
                      t_a.team_name AS team_a_name,
                      t_b.team_name AS team_b_name,
                      t_winner.team_name AS winner_team_name,
                      t_loser.team_name AS loser_team_name,
                      tourn.name AS tournament_name
               FROM DoublesMatches dm
               JOIN TournamentTeams tt_a ON dm.team_a_id = tt_a.id
               JOIN Teams t_a ON tt_a.team_id = t_a.id
               JOIN TournamentTeams tt_b ON dm.team_b_id = tt_b.id
               JOIN Teams t_b ON tt_b.team_id = t_b.id
               JOIN TournamentTeams tt_winner ON dm.winner_team_id = tt_winner.id
               JOIN Teams t_winner ON tt_winner.team_id = t_winner.id
               JOIN TournamentTeams tt_loser ON dm.loser_team_id = tt_loser.id
               JOIN Teams t_loser ON tt_loser.team_id = t_loser.id
               JOIN Tournaments tourn ON dm.tournament_id = tourn.id
               WHERE dm.tournament_id = ?
                 AND (t_a.gender_category = ? OR t_b.gender_category = ?)
               ORDER BY dm.date DESC''',
            (active_tournament_id, gender_filter, gender_filter)
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
    
    active_tournament_id = get_active_tournament_id_by_type('pyramid_single')
    if not active_tournament_id:
        return jsonify({"valid": False, "message": "No hay un torneo de pirámide individual activo para validar desafíos."}), 400

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
        active_tournament_id = get_active_tournament_id_by_type('pyramid_single')
        if not active_tournament_id:
            return jsonify({"error": "No hay un torneo de pirámide individual activo para proponer desafíos."}), 400

        existing_challenge = db.execute(
            '''SELECT id FROM Challenges WHERE challenger_id = ? AND challenged_id = ? AND status = 'pending' ''',
            (challenger_id, challenged_id)
        ).fetchone()

        if existing_challenge:
            print(f"DEBUG: [propose_challenge_api] Desafío ya existe (ID: {existing_challenge['id']}).")
            return jsonify({"error": "Ya existe un desafío pendiente entre estos jugadores."}), 409

        cursor.execute(
            '''INSERT INTO Challenges (tournament_id, challenger_id, challenged_id, status)
               VALUES (?, ?, ?, ?)''',
            (active_tournament_id, challenger_id, challenged_id, 'pending')
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
        # Obtener el ID del torneo pirámide individual activo/último para filtrar desafíos
        active_tournament_id = get_active_tournament_id_by_type('pyramid_single')
        if not active_tournament_id:
            return jsonify({"message": "No hay un torneo de pirámide individual activo para listar desafíos pendientes."}), 404

        pending_challenges_db = db.execute(
            '''SELECT c.id, c.challenger_id, c.challenged_id, c.status, c.created_at,
                      p_chal.first_name AS challenger_first_name, p_chal.last_name AS challenger_last_name,
                      p_chd.first_name AS challenged_first_name, p_chd.last_name AS challenged_last_name,
                      t.name AS tournament_name
               FROM Challenges c
               JOIN Players p_chal ON c.challenger_id = p_chal.id
               JOIN Players p_chd ON c.challenged_id = p_chd.id
               JOIN Tournaments t ON c.tournament_id = t.id -- Unir con Tournaments
               WHERE c.status = 'pending' AND c.tournament_id = ?
               ORDER BY c.created_at DESC''',
            (active_tournament_id,)
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
    challenge_id = data.get('challengeId') # ID del desafío pendiente, si se pasó

    if not all([challenger_id, challenged_id, sets]) or not (2 <= len(sets) <= 3):
        return jsonify({"error": "Datos de partido incompletos o número de sets incorrecto."}), 400

    db = get_db()
    cursor = db.cursor()
    
    try:
        active_tournament_id = get_active_tournament_id_by_type('pyramid_single')
        if not active_tournament_id:
            return jsonify({"error": "No hay un torneo de pirámide individual activo para registrar resultados."}), 400

        tournament_info = db.execute("SELECT type FROM Tournaments WHERE id = ?", (active_tournament_id,)).fetchone()
        if not tournament_info:
            return jsonify({"error": "Información del torneo activo no encontrada."}), 500
        
        is_pyramid_single_tournament = (tournament_info['type'] == 'pyramid_single')


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

        if is_pyramid_single_tournament:
            if challenger_won_match and challenger['current_position'] > challenged['current_position']:
                final_challenger_pos = challenged['current_position']
                final_challenged_pos = challenger['current_position']
                positions_swapped = True
                print(f"DEBUG: Standard swap - Challenger {challenger_id} won against {challenged_id}. Positions swapped.")

            elif not challenger_won_match and challenger['current_position'] == 1:
                final_challenger_pos = challenged['current_position']
                final_challenged_pos = challenger['current_position']
                positions_swapped = True
                print(f"DEBUG: Puesto 1 lost - Challenger {challenger_id} (P1) lost to {challenged_id}. Positions swapped.")

            cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (final_challenger_pos, challenger_id))
            cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (final_challenged_pos, challenged_id))
            
            cursor.execute("UPDATE Players SET challenges_emitted_single = challenges_emitted_single + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (challenger_id,))
            cursor.execute("UPDATE Players SET challenges_accepted_single = challenges_accepted_single + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (challenged_id,))
            
            if challenger_won_match:
                cursor.execute("UPDATE Players SET challenges_won_single = challenges_won_single + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (challenger_id,))
            else:
                cursor.execute("UPDATE Players SET defenses_successful_single = defenses_successful_single + 1, last_activity_update = CURRENT_TIMESTAMP WHERE id = ?", (challenged_id,))
            
            _recalculate_player_activity_status(challenger_id)
            _recalculate_player_activity_status(challenged_id)
        else:
            print(f"DEBUG: Partido individual en torneo tipo '{tournament_info['type']}' no afecta Ranking Maestro.")
            
        match_id_inserted = cursor.execute(
            """INSERT INTO Matches (tournament_id, date, challenger_id, challenged_id, winner_id, loser_id, score_text, is_challenger_winner, positions_swapped, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (active_tournament_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), challenger_id, challenged_id, winner_id, loser_id, score_text, challenger_won_match, positions_swapped, 'valid')
        ).lastrowid
        
        if match_id_inserted:
            cursor.execute(
                """INSERT INTO ActivityLog (player_id, event_type, challenge_id, match_id, tournament_id, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (challenger_id, 'match_played_single', challenge_id, match_id_inserted, active_tournament_id, f"Jugó individual contra {challenged['first_name']} {challenged['last_name']} en torneo {active_tournament_id}")
            )
            cursor.execute(
                """INSERT INTO ActivityLog (player_id, event_type, challenge_id, match_id, tournament_id, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (challenged_id, 'match_played_single', challenge_id, match_id_inserted, active_tournament_id, f"Jugó individual contra {challenger['first_name']} {challenger['last_name']} en torneo {active_tournament_id}")
            )
        
        if challenge_id:
            cursor.execute("UPDATE Challenges SET status = 'played' WHERE id = ?", (challenge_id,))
            print(f"DEBUG: [post_match_result_api] Desafío pendiente {challenge_id} marcado como 'played'.")
        
        db.commit()
        
        g.pop('db', None)
        db.close()
        return jsonify({"message": "Resultado procesado exitosamente."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [post_match_result_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error en la base de datos: {str(e)}"}), 500
    except Exception as e:
        db.rollback() 
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
        # Obtener el partido para saber sus IDs de jugadores, si hubo intercambio y a qué torneo pertenece
        match = db.execute('SELECT challenger_id, challenged_id, winner_id, loser_id, positions_swapped, tournament_id FROM Matches WHERE id = ?', (match_id,)).fetchone()
        if not match:
            return jsonify({"error": "Partido no encontrado."}), 404

        tournament_id = match['tournament_id'] # Obtener el ID del torneo del partido

        # Obtener información del torneo para la lógica condicional (pyramid vs satellite)
        tournament_info = db.execute("SELECT type FROM Tournaments WHERE id = ?", (tournament_id,)).fetchone()
        if not tournament_info:
            return jsonify({"error": "Información del torneo no encontrada."}), 500 # Esto no debería pasar

        is_pyramid_single_tournament = (tournament_info['type'] == 'pyramid_single')

        # --- LÓGICA DE REVERSIÓN DE POSICIONES Y ACTIVIDAD (SOLO SI ES PIRÁMIDE INDIVIDUAL) ---
        if is_pyramid_single_tournament:
            winner_id = match['winner_id']
            loser_id = match['loser_id']
            challenger_id = match['challenger_id']
            challenged_id = match['challenged_id']

            # 1. Revertir posiciones si hubo intercambio
            if match['positions_swapped']:
                winner_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (winner_id,)).fetchone()['current_position']
                loser_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (loser_id,)).fetchone()['current_position']

                # Intercambiar de nuevo las posiciones
                cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (loser_pos, winner_id))
                cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (winner_pos, loser_id))
                print(f"DEBUG: [delete_match_api] Posiciones revertidas para {winner_id} y {loser_id} en Ranking Maestro.")
            
            # 2. Revertir contadores de actividad en Players (Ranking Maestro)
            # Esto es más complejo y requiere decidir cómo revertir.
            # Por simplicidad, aquí solo revertimos posiciones. Revertir contadores
            # (challenges_emitted, accepted, won, etc.) es más detallado y puede
            # llevar a inconsistencias si no se maneja bien.
            # Si se desea revertir contadores, habría que restar 1 a los contadores
            # adecuados (ej. challenges_won_single para el ganador, etc.)
            # y luego llamar a _recalculate_player_activity_status para ambos jugadores.
            # Por ahora, solo revertimos posiciones y eliminamos el partido.
            
            # Recalcular actividad de los jugadores afectados (por si acaso, aunque contadores no se reviertan)
            _recalculate_player_activity_status(challenger_id)
            _recalculate_player_activity_status(challenged_id)
            print(f"DEBUG: [delete_match_api] Actividad de jugadores {challenger_id} y {challenged_id} recalculada.")

        else:
            print(f"DEBUG: [delete_match_api] Partido en torneo tipo '{tournament_info['type']}' no afecta Ranking Maestro. No se revierten posiciones ni actividad global.")
        # --- FIN LÓGICA DE REVERSIÓN ---

        # Eliminar el partido de la tabla Matches
        cursor.execute('DELETE FROM Matches WHERE id = ?', (match_id,))
        
        # Opcional: Eliminar entradas relacionadas en ActivityLog para este partido
        cursor.execute('DELETE FROM ActivityLog WHERE match_id = ?', (match_id,))
        print(f"DEBUG: [delete_match_api] Partido {match_id} y sus entradas en ActivityLog eliminados.")

        db.commit()
        return jsonify({"message": "Partido eliminado y posiciones revertidas exitosamente."}), 200
    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [delete_match_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al eliminar el partido: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [delete_match_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al eliminar el partido: {str(e)}"}), 500

@app.route('/api/doubles_challenges/<int:challenge_id>/reject', methods=['POST'])
@login_required
def mark_rejected_doubles_challenge_api(challenge_id):
    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener el desafío de dobles para saber quién es el equipo desafiado
        challenge = db.execute('SELECT team_b_id, status FROM DoublesMatches WHERE id = ?', (challenge_id,)).fetchone()
        if not challenge:
            return jsonify({"error": "Desafío de dobles no encontrado."}), 404
        
        if challenge['status'] != 'pending':
            return jsonify({"error": "El desafío de dobles ya no está pendiente."}), 400

        challenged_team_id = challenge['team_b_id']
        
        # Obtener los IDs de los jugadores del equipo desafiado (esto ya existe, lo mantenemos)
        challenged_team = db.execute('SELECT player1_id, player2_id FROM Teams WHERE id = ?', (challenged_team_id,)).fetchone()
        if not challenged_team:
            return jsonify({"error": "Equipo desafiado no encontrado."}), 404

        player1_challenged_id = challenged_team['player1_id']
        player2_challenged_id = challenged_team['player2_id']

        # Actualizar el contador de rechazos de AMBOS jugadores individuales (esto ya existe, lo mantenemos)
        cursor.execute(
            """UPDATE Players SET 
               rejections_current_cycle = rejections_current_cycle + 1, 
               rejections_total = rejections_total + 1,
               last_activity_update = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (player1_challenged_id,)
        )
        cursor.execute(
            """UPDATE Players SET 
               rejections_current_cycle = rejections_current_cycle + 1, 
               rejections_total = rejections_total + 1,
               last_activity_update = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (player2_challenged_id,)
        )
        
        # --- NUEVA LÓGICA DE ACTIVIDAD PARA EQUIPOS DE DOBLES ---
        # Actualizar el contador de rechazos del EQUIPO desafiado
        cursor.execute(
            """UPDATE Teams SET
               rejections_team_doubles_current_cycle = rejections_team_doubles_current_cycle + 1,
               rejections_team_doubles_total = rejections_team_doubles_total + 1,
               last_activity_team_doubles_update = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (challenged_team_id,)
        )
        # --- FIN NUEVA LÓGICA ---

        # Marcar el desafío de dobles como rechazado en la tabla DoublesMatches (esto ya existe, lo mantenemos)
        cursor.execute("UPDATE DoublesMatches SET status = 'rejected' WHERE id = ?", (challenge_id,))

        db.commit()

        # Recalcular el estado de actividad para ambos jugadores del equipo desafiado (esto ya existe, lo mantenemos)
        _recalculate_player_activity_status(player1_challenged_id)
        _recalculate_player_activity_status(player2_challenged_id)

        # --- NUEVA LLAMADA: Recalcular el estado de actividad para el EQUIPO desafiado ---
        _recalculate_team_doubles_activity_status(challenged_team_id)
        # --- FIN NUEVA LLAMADA ---

        return jsonify({"message": "Desafío de dobles marcado como rechazado exitosamente."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [mark_rejected_doubles_challenge_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al marcar desafío de dobles como rechazado: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [mark_rejected_doubles_challenge_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al marcar desafío de dobles como rechazado: {str(e)}"}), 500


@app.route('/api/doubles_challenges/<int:challenge_id>/ignore', methods=['POST'])
@login_required
def mark_ignored_doubles_challenge_api(challenge_id):
    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener el desafío de dobles para saber quién es el equipo desafiante
        challenge = db.execute('SELECT team_a_id, status FROM DoublesMatches WHERE id = ?', (challenge_id,)).fetchone()
        if not challenge:
            return jsonify({"error": "Desafío de dobles no encontrado."}), 404
        
        if challenge['status'] != 'pending':
            return jsonify({"error": "El desafío de dobles ya no está pendiente."}), 400

        challenger_team_id = challenge['team_a_id']

        # Obtener los IDs de los jugadores del equipo desafiante (esto ya existe, lo mantenemos)
        challenger_team = db.execute('SELECT player1_id, player2_id FROM Teams WHERE id = ?', (challenger_team_id,)).fetchone()
        if not challenger_team:
            return jsonify({"error": "Equipo desafiante no encontrado."}), 404

        player1_challenger_id = challenger_team['player1_id']
        player2_challenger_id = challenger_team['player2_id']

        # Otorgar +1 punto simbólico en el índice de actividad de dobles de AMBOS jugadores individuales (esto ya existe, lo mantenemos)
        cursor.execute(
            """UPDATE Players SET 
               activity_index_doubles = activity_index_doubles + 1, 
               last_activity_update = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (player1_challenger_id,)
        )
        cursor.execute(
            """UPDATE Players SET 
               activity_index_doubles = activity_index_doubles + 1, 
               last_activity_update = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (player2_challenger_id,)
        )
        
        # --- NUEVA LÓGICA DE ACTIVIDAD PARA EQUIPOS DE DOBLES ---
        # Otorgar +1 punto simbólico en el índice de actividad del EQUIPO desafiante
        cursor.execute(
            """UPDATE Teams SET
               activity_index_team_doubles = activity_index_team_doubles + 1,
               last_activity_team_doubles_update = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (challenger_team_id,)
        )
        # --- FIN NUEVA LÓGICA ---

        # Marcar el desafío de dobles como ignorado en la tabla DoublesMatches (esto ya existe, lo mantenemos)
        cursor.execute("UPDATE DoublesMatches SET status = 'ignored' WHERE id = ?", (challenge_id,))

        db.commit()

        # Recalcular el estado de actividad para ambos jugadores del equipo desafiante (esto ya existe, lo mantenemos)
        _recalculate_player_activity_status(player1_challenger_id)
        _recalculate_player_activity_status(player2_challenger_id)

        # --- NUEVA LLAMADA: Recalcular el estado de actividad para el EQUIPO desafiante ---
        _recalculate_team_doubles_activity_status(challenger_team_id)
        # --- FIN NUEVA LLAMADA ---

        return jsonify({"message": "Desafío de dobles marcado como ignorado y retadores compensados."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [mark_ignored_doubles_challenge_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al marcar desafío de dobles como ignorado: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [mark_ignored_doubles_challenge_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al marcar desafío de dobles como ignorado: {str(e)}"}), 500

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
                      m.tournament_id, -- NUEVO: Obtener el ID del torneo
                      p_chal.first_name AS challenger_first_name, p_chal.last_name AS challenger_last_name,
                      p_chd.first_name AS challenged_first_name, p_chd.last_name AS challenged_last_name,
                      t.name AS tournament_name -- NUEVO: Nombre del torneo
               FROM Matches m
               JOIN Players p_chal ON m.challenger_id = p_chal.id
               JOIN Players p_chd ON m.challenged_id = p_chd.id
               JOIN Tournaments t ON m.tournament_id = t.id -- NUEVO: Unir con Tournaments
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
        # match_dict['tournament_name'] ya está incluido por el SELECT
        
        return jsonify(match_dict), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_match_details_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener detalles del partido: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_match_details_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener detalles del partido: {str(e)}"}), 500

# En app.py, dentro de la sección de "API Endpoints"

# ... (código existente) ...

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
        # Obtener el partido original para sus IDs de jugadores, si hubo intercambio y a qué torneo pertenece
        original_match = db.execute(
            'SELECT challenger_id, challenged_id, winner_id, loser_id, positions_swapped, tournament_id FROM Matches WHERE id = ?',
            (match_id,)
        ).fetchone()

        if not original_match:
            return jsonify({"error": "Partido original no encontrado."}), 404

        tournament_id = original_match['tournament_id'] # Obtener el ID del torneo del partido

        # Obtener información del torneo para la lógica condicional (pyramid vs satellite)
        tournament_info = db.execute("SELECT type FROM Tournaments WHERE id = ?", (tournament_id,)).fetchone()
        if not tournament_info:
            return jsonify({"error": "Información del torneo no encontrada."}), 500 # Esto no debería pasar

        is_pyramid_single_tournament = (tournament_info['type'] == 'pyramid_single')


        original_challenger_id = original_match['challenger_id']
        original_challenged_id = original_match['challenged_id']
        original_winner_id = original_match['winner_id']
        original_loser_id = original_match['loser_id']
        original_positions_swapped = original_match['positions_swapped']

        # --- Lógica de reversión y nueva aplicación de posiciones/actividad (SOLO si es PIRÁMIDE INDIVIDUAL) ---
        if is_pyramid_single_tournament:
            # 1. Revertir posiciones a su estado ANTERIOR al partido si hubo intercambio
            if original_positions_swapped:
                # Si las posiciones se intercambiaron, las revertimos a como estaban antes del partido
                # (el ganador vuelve a la posición del perdedor, y el perdedor a la del ganador)
                winner_current_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (original_winner_id,)).fetchone()['current_position']
                loser_current_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (original_loser_id,)).fetchone()['current_position']
                
                cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (loser_current_pos, original_winner_id))
                cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (winner_current_pos, original_loser_id))
                print(f"DEBUG: [edit_match_api] Posiciones originales revertidas para {original_winner_id} y {original_loser_id} en Ranking Maestro.")
            
            # NOTA: Revertir contadores de actividad (challenges_won_single, etc.) es MUY complejo y propenso a errores.
            # Por ahora, solo nos centramos en las posiciones y la actividad recalculada.
            # Si se desea revertir contadores, se necesita un sistema de logs de actividad mucho más granular.

            # 2. Recalcular contadores de actividad de los jugadores afectados (por si acaso)
            _recalculate_player_activity_status(original_challenger_id)
            _recalculate_player_activity_status(original_challenged_id)
            print(f"DEBUG: [edit_match_api] Actividad de jugadores {original_challenger_id} y {original_challenged_id} recalculada después de reversión.")
        else:
            print(f"DEBUG: [edit_match_api] Partido en torneo tipo '{tournament_info['type']}' no afecta Ranking Maestro. No se revierten posiciones ni actividad global.")
        # --- FIN LÓGICA DE REVERSIÓN ---


        new_chal_sets_won = sum(1 for s in new_sets if s[0] > s[1])
        new_chd_sets_won = len(new_sets) - new_chal_sets_won

        if not ((new_chal_sets_won == 2 and new_chd_sets_won < 2) or (new_chd_sets_won == 2 and new_chal_sets_won < 2)):
            return jsonify({"error": "Resultado de sets inválido: un jugador debe ganar 2 sets."}), 400

        new_score_text = ", ".join([f"{s[0]}-{s[1]}" for s in new_sets])
        new_challenger_won_match = new_chal_sets_won > new_chd_sets_won
        new_winner_id = original_challenger_id if new_challenger_won_match else original_challenged_id
        new_loser_id = original_challenged_id if new_challenger_won_match else original_challenger_id

        new_positions_swapped = False
        
        # --- Lógica de APLICACIÓN de nuevas posiciones y actividad (SOLO si es PIRÁMIDE INDIVIDUAL) ---
        if is_pyramid_single_tournament:
            # Obtener las posiciones actuales después de la posible reversión
            current_challenger_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (original_challenger_id,)).fetchone()['current_position']
            current_challenged_pos = db.execute('SELECT current_position FROM Players WHERE id = ?', (original_challenged_id,)).fetchone()['current_position']

            final_challenger_pos = current_challenger_pos
            final_challenged_pos = current_challenged_pos

            # Aplicar las reglas de intercambio de posición con el NUEVO resultado
            if new_challenger_won_match and current_challenger_pos > current_challenged_pos:
                final_challenger_pos, final_challenged_pos = current_challenged_pos, current_challenger_pos
                new_positions_swapped = True
                print(f"DEBUG: [edit_match_api] Nuevo intercambio de posiciones aplicado: {original_challenger_id} y {original_challenged_id}.")
            elif not new_challenger_won_match and current_challenger_pos == 1: # Si el P1 desafió y perdió
                 final_challenger_pos, final_challenged_pos = current_challenged_pos, current_challenger_pos
                 new_positions_swapped = True
                 print(f"DEBUG: [edit_match_api] P1 perdió, nuevo intercambio de posiciones aplicado: {original_challenger_id} y {original_challenged_id}.")
            
            cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (final_challenger_pos, original_challenger_id))
            cursor.execute("UPDATE Players SET current_position = ? WHERE id = ?", (final_challenged_pos, original_challenged_id))
            print(f"DEBUG: [edit_match_api] Nuevas posiciones aplicadas: {original_challenger_id} a {final_challenger_pos}, {original_challenged_id} a {final_challenged_pos}.")

            # NOTA: La actividad (challenges_emitted, accepted, won, etc.) no se "edita" directamente.
            # Se recalcula después de la reversión y la nueva aplicación.
            # Si se necesita una reversión precisa de contadores, el ActivityLog debería ser el punto de verdad.
            _recalculate_player_activity_status(original_challenger_id)
            _recalculate_player_activity_status(original_challenged_id)
            print(f"DEBUG: [edit_match_api] Actividad de jugadores {original_challenger_id} y {original_challenged_id} recalculada después de nueva aplicación.")
        else:
            print(f"DEBUG: [edit_match_api] Partido en torneo tipo '{tournament_info['type']}' no afecta Ranking Maestro. No se aplican nuevas posiciones ni actividad global.")
        # --- FIN LÓGICA DE APLICACIÓN ---

        # Actualizar el partido en la tabla Matches
        cursor.execute(
            """UPDATE Matches SET score_text = ?, winner_id = ?, loser_id = ?, is_challenger_winner = ?, positions_swapped = ?
               WHERE id = ?""",
            (new_score_text, new_winner_id, new_loser_id, new_challenger_won_match, new_positions_swapped, match_id)
        )
        
        db.commit()
        print(f"DEBUG: [edit_match_api] Partido {match_id} editado exitosamente.")
        return jsonify({"message": "Partido editado exitosamente y posiciones actualizadas."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [edit_match_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al editar el partido: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [edit_match_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al editar el partido: {str(e)}"}), 500

@app.route('/api/challenges/<int:challenge_id>/reject', methods=['POST'])
@login_required
def mark_rejected_challenge_api(challenge_id):
    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener el desafío para saber quién es el desafiado y a qué torneo pertenece
        challenge = db.execute('SELECT challenged_id, status, tournament_id FROM Challenges WHERE id = ?', (challenge_id,)).fetchone()
        if not challenge:
            return jsonify({"error": "Desafío no encontrado."}), 404
        
        if challenge['status'] != 'pending':
            return jsonify({"error": "El desafío ya no está pendiente."}), 400

        challenged_player_id = challenge['challenged_id']
        tournament_id = challenge['tournament_id'] # Obtener el ID del torneo del desafío

        # Obtener información del torneo para la lógica condicional (pyramid vs satellite)
        tournament_info = db.execute("SELECT type FROM Tournaments WHERE id = ?", (tournament_id,)).fetchone()
        if not tournament_info:
            return jsonify({"error": "Información del torneo no encontrada."}), 500 # Esto no debería pasar

        is_pyramid_single_tournament = (tournament_info['type'] == 'pyramid_single')

        # --- LÓGICA DE ACTIVIDAD PARA JUGADORES INDIVIDUALES (RANKING MAESTRO) ---
        # Solo si es un torneo pirámide individual
        if is_pyramid_single_tournament:
            # Actualizar el contador de rechazos del jugador desafiado
            cursor.execute(
                """UPDATE Players SET 
                   rejections_current_cycle = rejections_current_cycle + 1, 
                   rejections_total = rejections_total + 1,
                   last_activity_update = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (challenged_player_id,)
            )
            # Recalcular el estado de actividad del jugador desafiado
            _recalculate_player_activity_status(challenged_player_id)
        else:
            print(f"DEBUG: Desafío individual rechazado en torneo tipo '{tournament_info['type']}' no afecta rechazos de Ranking Maestro.")
        # --- FIN LÓGICA JUGADORES INDIVIDUALES ---
        
        # Marcar el desafío como rechazado en la tabla Challenges
        cursor.execute("UPDATE Challenges SET status = 'rejected' WHERE id = ?", (challenge_id,))

        db.commit()

        return jsonify({"message": "Desafío marcado como rechazado exitosamente."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [mark_rejected_challenge_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al marcar desafío como rechazado: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [mark_rejected_challenge_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al marcar desafío como rechazado: {str(e)}"}), 500
    
# En app.py, dentro de la sección de "API Endpoints"

@app.route('/api/challenges/<int:challenge_id>/ignore', methods=['POST'])
@login_required
def mark_ignored_challenge_api(challenge_id):
    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener el desafío para saber quién es el desafiante y a qué torneo pertenece
        challenge = db.execute('SELECT challenger_id, status, tournament_id FROM Challenges WHERE id = ?', (challenge_id,)).fetchone()
        if not challenge:
            return jsonify({"error": "Desafío no encontrado."}), 404

        if challenge['status'] != 'pending':
            return jsonify({"error": "El desafío ya no está pendiente."}), 400

        challenger_player_id = challenge['challenger_id']
        tournament_id = challenge['tournament_id'] # Obtener el ID del torneo del desafío

        # Obtener información del torneo para la lógica condicional (pyramid vs satellite)
        tournament_info = db.execute("SELECT type FROM Tournaments WHERE id = ?", (tournament_id,)).fetchone()
        if not tournament_info:
            return jsonify({"error": "Información del torneo no encontrada."}), 500 # Esto no debería pasar

        is_pyramid_single_tournament = (tournament_info['type'] == 'pyramid_single')

        # --- LÓGICA DE ACTIVIDAD PARA JUGADORES INDIVIDUALES (RANKING MAESTRO) ---
        # Solo si es un torneo pirámide individual
        if is_pyramid_single_tournament:
            # Otorgar +1 punto simbólico en el índice de actividad del desafiante
            cursor.execute(
                """UPDATE Players SET 
                   activity_index_single = activity_index_single + 1,  
                   last_activity_update = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (challenger_player_id,)
            )
            # Recalcular el estado de actividad del desafiante
            _recalculate_player_activity_status(challenger_player_id)
        else:
            print(f"DEBUG: Desafío individual ignorado en torneo tipo '{tournament_info['type']}' no afecta actividad de Ranking Maestro.")
        # --- FIN LÓGICA JUGADORES INDIVIDUALES ---

        # Marcar el desafío como ignorado en la tabla Challenges
        cursor.execute("UPDATE Challenges SET status = 'ignored' WHERE id = ?", (challenge_id,))

        db.commit()

        return jsonify({"message": "Desafío marcado como ignorado y retador compensado."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [mark_ignored_challenge_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al marcar desafío como ignorado: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [mark_ignored_challenge_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al marcar desafío como ignorado: {str(e)}"}), 500

@app.route('/api/reset_cycle_activity', methods=['POST'])
@login_required
def reset_cycle_activity_api():
    db = get_db()
    cursor = db.cursor()
    try:
        # Reiniciar el contador de rechazos por ciclo para todos los jugadores
        cursor.execute("UPDATE Players SET rejections_current_cycle = 0, last_activity_update = CURRENT_TIMESTAMP")
        
        # Actualizar la fecha de inicio del ciclo en TournamentSettings
        cursor.execute(
            """INSERT OR REPLACE INTO TournamentSettings (setting_name, setting_value)
               VALUES (?, ?)""",
            ('cycle_start_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        
        # Recalcular el estado de actividad de todos los jugadores después de reiniciar los contadores
        # Esto llama a _recalculate_player_activity_status para cada jugador
        _recalculate_all_players_activity_status()
        
        # El commit final para todas las operaciones (reset de rechazos, actualización de settings y recálculos)
        db.commit() 

        return jsonify({"message": "Ciclo de actividad reiniciado exitosamente."}), 200
    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [reset_cycle_activity_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al reiniciar ciclo de actividad: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [reset_cycle_activity_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al reiniciar ciclo de actividad: {str(e)}"}), 500

@app.route('/login', methods=['GET', 'POST'])
def login(): # <<< Esta es la función a la que url_for('login') debería apuntar
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')

        db = get_db()
        user = None

        # Intentar buscar por username
        user = db.execute(
            "SELECT * FROM Users WHERE username = ?", (username_or_email,)
        ).fetchone()

        # Si no se encuentra por username, intentar buscar por email
        if not user:
            user = db.execute(
                "SELECT * FROM Users WHERE email = ?", (username_or_email,)
            ).fetchone()

        # --- DEBUGGING TEMPORAL DE LOGIN ---
        print(f"DEBUG LOGIN: Intentando login para username/email: {username_or_email}")
        print(f"DEBUG LOGIN: Contraseña ingresada: {password}")
        if user:
            print(f"DEBUG LOGIN: Usuario encontrado: {user['username']}")
            print(f"DEBUG LOGIN: Hash almacenado: {user['password_hash']}")
            if check_password_hash(user['password_hash'], password):
                print("DEBUG LOGIN: check_password_hash RETURNED TRUE")
            else:
                print("DEBUG LOGIN: check_password_hash RETURNED FALSE - Contraseña no coincide")
        else:
            print("DEBUG LOGIN: Usuario NO encontrado en la base de datos.")
        # --- FIN DEBUGGING ---

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session['email'] = user['email']
            
            # --- LÓGICA PARA CARGAR player_id EN LA SESIÓN ---
            linked_player_data = db.execute(
                "SELECT player_id FROM UserPlayersLink WHERE user_id = ?", (user['id'],)
            ).fetchone()
            if linked_player_data:
                session['player_id'] = linked_player_data['player_id']
                print(f"DEBUG LOGIN: Player ID {session['player_id']} vinculado y cargado en sesión.")
            else:
                session['player_id'] = None # Asegurarse de que sea None si no hay vínculo
                print("DEBUG LOGIN: No hay perfil de jugador vinculado para este usuario.")
            # --- FIN LÓGICA player_id ---
            
            # Lógica de redirección basada en el rol y el perfil de jugador
            if user['is_admin']:
                flash('Bienvenido al panel de organizador.', 'success')
                return redirect(url_for('organizer_page'))
            else:
                # Si el usuario no es admin y no tiene player_id, redirigir a completar perfil
                if session['player_id'] is None:
                    flash('Bienvenido. Por favor, completa tu perfil de jugador para acceder al sistema.', 'info')
                    return redirect(url_for('complete_player_profile')) # Asegúrate de que esta es la ruta de tu página
                else:
                    flash(f"Bienvenido de nuevo, {user['username']}.", 'success')
                    return redirect(url_for('player_dashboard_page')) # Asegúrate de que esta es la ruta de tu página

        else:
            flash('Nombre de usuario/Email o contraseña incorrectos.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    session.pop('email', None) # Asegurarse de limpiar también el email
    session.pop('player_id', None) # <<-- Asegurarse de que player_id se limpie
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

# --- NUEVAS RUTAS DE REGISTRO DE USUARIOS ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        db = get_db()
        cursor = db.cursor()

        # Validaciones básicas
        if not username or not email or not password or not confirm_password:
            flash('Todos los campos son requeridos.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('register.html')

        # Verificar si el username ya existe
        existing_user_by_username = db.execute(
            "SELECT id FROM Users WHERE username = ?", (username,)
        ).fetchone()
        if existing_user_by_username:
            flash('El nombre de usuario ya está en uso. Por favor, elija otro.', 'error')
            return render_template('register.html')

        # Verificar si el email ya existe en Users
        existing_user_by_email = db.execute(
            "SELECT id FROM Users WHERE email = ?", (email,)
        ).fetchone()
        if existing_user_by_email:
            flash('Este email ya está registrado. Por favor, inicie sesión o use otro email.', 'error')
            return render_template('register.html')

        try:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO Users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, 0) # is_admin por defecto a 0 para nuevos registros
            )
            db.commit()

            new_user_id = cursor.lastrowid
            
            # --- ELIMINAR LÓGICA DE VINCULACIÓN AUTOMÁTICA CON JUGADOR EXISTENTE POR EMAIL AQUÍ ---
            # Esta lógica se moverá al POST /complete_player_profile
            
            # Flash message and redirect to complete profile
            flash('Registro exitoso. Por favor, completa tu perfil de jugador.', 'success')
            print(f"DEBUG: Usuario {username} (ID: {new_user_id}) registrado. Redirigiendo a completar perfil.")

            # Log the user in immediately after registration
            session['user_id'] = new_user_id
            session['username'] = username
            session['is_admin'] = 0
            session['email'] = email # Store email in session

            return redirect(url_for('complete_player_profile'))

        except sqlite3.Error as e:
            db.rollback()
            flash(f"Error de base de datos al registrar: {e}", 'error')
            print(f"ERROR DB: [register] {e}")
        except Exception as e:
            db.rollback()
            flash(f"Error inesperado al registrar: {e}", 'error')
            print(f"ERROR GENERICO: [register] {e}")

    return render_template('register.html')

# --- RUTAS DE PÁGINAS WEB (Vistas) ---
# Necesitarás crear estas rutas básicas para la redirección post-login de jugadores



# En app.py, dentro de la sección de "API Endpoints"

@app.route('/api/player_data/me', methods=['GET'])
@login_required
def get_my_player_data_api():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Usuario no autenticado."}), 401

    db = get_db()
    
    # Obtener el player_id vinculado al user_id actual
    linked_player = db.execute(
        "SELECT player_id FROM UserPlayersLink WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not linked_player:
        return jsonify({"error": "Tu cuenta de usuario no está vinculada a un perfil de jugador."}), 404
    
    player_id = linked_player['player_id']

    try: # Esta es la línea 'try:' en tu código (aprox. línea 2027)
        # Obtener toda la información detallada del jugador
        player_data_db = db.execute(
            '''SELECT id, first_name, last_name, email, phone, gender,
                        birth_date, location, dominant_hand, backhand_type, racquet,
                        photo_url, initial_position, current_position, points,
                        activity_index_single, challenges_emitted_single, challenges_accepted_single,
                        challenges_won_single, defenses_successful_single, activity_status_single,
                        activity_index_doubles, challenges_emitted_doubles, challenges_accepted_doubles,
                        challenges_won_doubles, defenses_successful_doubles, activity_status_doubles,
                        rejections_current_cycle, rejections_total, activity_status, last_activity_update,
                        last_challenge_received_date
                FROM Players WHERE id = ?''', (player_id,)
        ).fetchone()

        if not player_data_db:
            return jsonify({"error": "Perfil de jugador no encontrado."}), 404

        player_dict = dict(player_data_db)
        player_dict['full_name'] = f"{player_data_db['first_name']} {player_data_db['last_name']}"

        # Formatear la última actualización de actividad para mostrar en el frontend
        if player_dict['last_activity_update']:
            try:
                dt_object = datetime.strptime(player_dict['last_activity_update'], '%Y-%m-%d %H:%M:%S')
                player_dict['last_activity_update_formatted'] = dt_object.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                player_dict['last_activity_update_formatted'] = 'N/A'
        else:
            player_dict['last_activity_update_formatted'] = 'Nunca'

        return jsonify(player_dict), 200

    except sqlite3.Error as e: # <-- Esta línea (2039) debe tener la misma indentación que 'try:'
        print(f"ERROR DB: [get_my_player_data_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos: {str(e)}"}), 500
    except Exception as e: # <-- Esta línea también
        print(f"ERROR GENERICO: [get_my_player_data_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener datos del jugador: {str(e)}"}), 500

@app.route('/api/players/search_partners', methods=['GET'])
@login_required
def search_doubles_partners_api():
    user_id = session.get('user_id')
    db = get_db()
    
    linked_player_row = db.execute(
        "SELECT player_id FROM UserPlayersLink WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not linked_player_row:
        return jsonify({"error": "Tu cuenta no está vinculada a un perfil de jugador."}), 400
    
    current_player_id = linked_player_row['player_id']

    # --- NUEVOS PARÁMETROS: tournament_id y el género del torneo ---
    tournament_id = request.args.get('tournament_id', type=int)
    tournament_gender_type = request.args.get('tournament_gender_type') # Ej: 'pyramid_doubles_male', 'satellite_doubles_mixed'
    
    if not tournament_id or not tournament_gender_type:
        return jsonify({"error": "Se requiere el ID del torneo y su tipo de género para buscar compañeros."}), 400

    # Obtener el género del jugador actual
    current_player_gender_row = db.execute(
        "SELECT gender FROM Players WHERE id = ?", (current_player_id,)
    ).fetchone()

    if not current_player_gender_row:
        return jsonify({"error": "Perfil de jugador actual no encontrado."}), 404
    
    current_player_gender = current_player_gender_row['gender']

    search_term = request.args.get('q', '').strip()
    
    query = '''
        SELECT p.id, p.first_name, p.last_name, p.current_position, p.gender
        FROM Players p
        LEFT JOIN TournamentTeams tt ON (p.id = (SELECT player1_id FROM Teams WHERE id = tt.team_id) OR p.id = (SELECT player2_id FROM Teams WHERE id = tt.team_id)) AND tt.tournament_id = ?
        WHERE p.id != ?
          AND p.gender = ?
          AND tt.id IS NULL -- Asegura que el jugador NO esté actualmente en un equipo *para este torneo*
    '''
    # NOTA: La lógica de `tt.id IS NULL` con `LEFT JOIN` es más robusta.
    # Necesitas que `p.gender` coincida con el `gender` del `current_player_gender`.
    # Y que `tt.tournament_id = ?` filtre solo para el torneo actual.

    params = [tournament_id, current_player_id, current_player_gender] # El tournament_id va primero para el LEFT JOIN
    
    if search_term:
        query += " AND (p.first_name LIKE ? OR p.last_name LIKE ?)"
        params.extend([f'%{search_term}%', f'%{search_term}%'])
    
    query += " ORDER BY p.current_position ASC"

    try:
        eligible_partners_db = db.execute(query, params).fetchall()
        
        partners = []
        for p in eligible_partners_db:
            partner_dict = dict(p)
            partner_dict['name'] = f"{p['first_name']} {p['last_name']}"
            partners.append(partner_dict)
        
        return jsonify(partners), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [search_doubles_partners_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al buscar compañeros: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [search_doubles_partners_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al buscar compañeros: {str(e)}"}), 500
    

@app.route('/api/tournaments', methods=['POST'])
@login_required
def create_tournament():
    data = request.get_json()
    name = data.get('name')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    # registration_start_date_str y registration_end_date_str ya no se obtienen directamente del JSON
    # se calcularán o se tomarán del JSON solo si vienen definidos para sobrescribir el default.
    tournament_type = data.get('type')
    description = data.get('description')
    rules_url = data.get('rules_url')

    category = data.get('category')
    max_slots = data.get('max_slots', 0)
    cost = data.get('cost', 0.0)
    requirements = data.get('requirements')
    location = data.get('location')
    is_published = data.get('is_published', 0) # Default a 0 (oculto)

    organizer_id = session.get('user_id')
    if not organizer_id:
        return jsonify({"error": "No se pudo identificar al organizador."}), 401 # Unauthorized

    if not all([name, start_date_str, end_date_str, tournament_type]):
        return jsonify({"error": "Faltan datos obligatorios para crear el torneo (nombre, fechas, tipo)."}), 400

    try:
        # --- NUEVAS VALIDACIONES Y PREDETERMINACIONES DE FECHAS ---

        # 1. Eliminar la hora en la fecha del torneo: Convertir a objetos date, luego a string solo con la fecha
        #    Y validar formato antes de convertir
        try:
            tournament_start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
            tournament_end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({"error": "Formato de fecha de torneo inválido. Use YYYY-MM-DD HH:MM:SS."}), 400

        # Convertir a formato de solo fecha y luego a string para almacenar
        start_date_only = tournament_start_date_obj.strftime('%Y-%m-%d')
        end_date_only = tournament_end_date_obj.strftime('%Y-%m-%d')

        # 2. Validar que la fecha de fin no sea menor a la fecha de inicio
        if tournament_start_date_obj > tournament_end_date_obj:
            return jsonify({"error": "La fecha de fin del torneo no puede ser anterior a la fecha de inicio."}), 400

        # 3. Fecha de inicio de registro: actual (predeterminada)
        # 4. Fecha de fin de registro: misma fecha + 12 horas (predeterminada)
        current_datetime = datetime.now()
        
        # Intentar obtener fechas de registro del JSON si se proporcionan, sino usar por defecto
        # Primero convertimos las fechas a un formato que SQLite maneja mejor (TEXT)
        registration_start_date = data.get('registration_start_date')
        if registration_start_date: # Si viene en el JSON, la validamos y usamos
            try:
                registration_start_date_obj = datetime.strptime(registration_start_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return jsonify({"error": "Formato de fecha de inicio de registro inválido. Use YYYY-MM-DD HH:MM:SS."}), 400
        else: # Si no viene en el JSON, usamos la fecha y hora actual
            registration_start_date_obj = current_datetime

        registration_end_date = data.get('registration_end_date')
        if registration_end_date: # Si viene en el JSON, la validamos y usamos
            try:
                registration_end_date_obj = datetime.strptime(registration_end_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return jsonify({"error": "Formato de fecha de fin de registro inválido. Use YYYY-MM-DD HH:MM:SS."}), 400
        else: # Si no viene en el JSON, usamos la fecha de inicio de registro + 12 horas
            registration_end_date_obj = registration_start_date_obj + timedelta(hours=12)

        # Validaciones adicionales para fechas de registro
        if registration_start_date_obj >= registration_end_date_obj:
            return jsonify({"error": "La fecha de inicio de registro debe ser anterior a la fecha de fin de registro."}), 400
        
        # Convertir objetos datetime a strings para SQLite
        registration_start_date_sql = registration_start_date_obj.strftime('%Y-%m-%d %H:%M:%S')
        registration_end_date_sql = registration_end_date_obj.strftime('%Y-%m-%d %H:%M:%S')

        # --- FIN NUEVAS VALIDACIONES Y PREDETERMINACIONES DE FECHAS ---

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """INSERT INTO Tournaments (
                name, start_date, end_date, registration_start_date, registration_end_date,
                type, status, description, rules_url,
                category, max_slots, cost, requirements, location, is_published, organizer_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                start_date_only, # Usamos la fecha sin hora para el torneo
                end_date_only,   # Usamos la fecha sin hora para el torneo
                registration_start_date_sql, # Usamos la fecha y hora para el registro
                registration_end_date_sql,   # Usamos la fecha y hora para el registro
                tournament_type, 'registration_open', description, rules_url,
                category, max_slots, cost, requirements, location, is_published, organizer_id
            )
        )

        db.commit()
        return jsonify({"message": "Torneo creado exitosamente.", "tournament_id": cursor.lastrowid}), 201

    except ValueError as ve:
        # Capturar errores de formato de fecha específicos
        return jsonify({"error": f"Error de formato de fecha: {ve}. Use YYYY-MM-DD HH:MM:SS."}), 400
    except sqlite3.IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: Tournaments.name" in str(e):
            return jsonify({"error": "Ya existe un torneo con este nombre."}), 409
        print(f"ERROR DB: [create_tournament] Error de integridad de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al crear torneo (integridad): {str(e)}"}), 500
    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [create_tournament] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al crear torneo: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [create_tournament] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al crear torneo: {str(e)}"}), 500

# NUEVO ENDPOINT: Listar todos los Torneos
@app.route('/api/tournaments', methods=['GET'])
@login_required # Solo el organizador puede listar/gestionar torneos
def get_all_tournaments():
    db = get_db()
    try:
        tournaments_db = db.execute(
            '''SELECT id, name, start_date, end_date, registration_start_date, registration_end_date, type, status, description, rules_url, is_active, created_at
               FROM Tournaments ORDER BY start_date DESC'''
        ).fetchall()
        
        tournaments = [dict(t) for t in tournaments_db]
        return jsonify(tournaments), 200
    except sqlite3.Error as e:
        print(f"ERROR DB: [get_all_tournaments] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al listar torneos: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_all_tournaments] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al listar torneos: {str(e)}"}), 500

@app.route('/api/tournaments/<int:tournament_id>/update_status', methods=['POST'])
@login_required
def update_tournament_status(tournament_id):
    # Debug: Confirmar el ID recibido
    print(f"DEBUG update_tournament_status: Recibida petición para tournament_id={tournament_id} (Tipo: {type(tournament_id)})")

    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({"error": "Se requiere un nuevo estado para el torneo."}), 400

    db = get_db()
    cursor = db.cursor()
    
    try:
        # Debug: Mostrar la consulta y el parámetro
        print(f"DEBUG update_tournament_status: Ejecutando SELECT para Torneo WHERE id = {tournament_id}")
        tournament = db.execute("SELECT id, type, status, name FROM Tournaments WHERE id = ?", (tournament_id,)).fetchone()
        
        # Debug: Verificar el resultado de fetchone()
        if tournament:
            print(f"DEBUG update_tournament_status: Torneo encontrado: {dict(tournament)}")
        else:
            print(f"DEBUG update_tournament_status: Torneo con ID {tournament_id} NO encontrado por fetchone().")
            return jsonify({"error": "Torneo no encontrado (verificación interna)."}) # Mensaje más específico para depuración
        
        # Si llegamos aquí, 'tournament' no es None. El error 'No item with that key' no debería ocurrir en este bloque.
        # El error debe estar en las líneas siguientes si 'tournament' es None aquí.
        current_tournament_type = tournament['type'] # Esto es lo que causaría 'No item with that key' si tournament fuera None
        current_tournament_status = tournament['status']
        tournament_name = tournament['name'] 
        
        is_pyramid_type = current_tournament_type.startswith('pyramid_')
        
        if is_pyramid_type:
            if new_status in ['in_progress', 'registration_open']:
                print(f"DEBUG update_tournament_status: Es pirámide, activando {tournament_id} y desactivando otros de tipo {current_tournament_type}")
                cursor.execute(
                    "UPDATE Tournaments SET is_active = 0 WHERE type = ? AND id != ?",
                    (current_tournament_type, tournament_id)
                )
                cursor.execute(
                    "UPDATE Tournaments SET status = ?, is_active = 1 WHERE id = ?",
                    (new_status, tournament_id)
                )
            else:
                print(f"DEBUG update_tournament_status: Es pirámide, desactivando {tournament_id} por estado {new_status}")
                cursor.execute(
                    "UPDATE Tournaments SET status = ?, is_active = 0 WHERE id = ?",
                    (new_status, tournament_id)
                )
        else: # Si es un torneo satélite, simplemente actualizar el status
            print(f"DEBUG update_tournament_status: Es satélite, actualizando estado a {new_status}")
            cursor.execute(
                "UPDATE Tournaments SET status = ? WHERE id = ?",
                (new_status, tournament_id)
            )

        db.commit()
        print(f"DEBUG update_tournament_status: Commit exitoso.")
        return jsonify({"message": f"Estado del torneo '{tournament_name}' actualizado a '{new_status}'."}), 200

    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [update_tournament_status] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al actualizar estado del torneo: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [update_tournament_status] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al actualizar estado del torneo: {str(e)}"}), 500

@app.route('/api/global_doubles_teams', methods=['GET'])
@login_required # Proteger este endpoint para que solo el organizador acceda a la lista completa
def get_global_doubles_teams_api():
    db = get_db()
    try:
        # Selecciona todos los equipos de la tabla Teams y sus jugadores
        teams_db = db.execute(
            '''
            SELECT t.id, t.player1_id, t.player2_id, t.team_name, t.gender_category, t.created_at,
                   p1.first_name AS p1_first_name, p1.last_name AS p1_last_name,
                   p2.first_name AS p2_first_name, p2.last_name AS p2_last_name
            FROM Teams t
            JOIN Players p1 ON t.player1_id = p1.id
            JOIN Players p2 ON t.player2_id = p2.id
            ORDER BY t.team_name ASC -- O por alguna otra lógica si prefieres
            '''
        ).fetchall()

        teams = []
        for t in teams_db:
            team_dict = dict(t)
            team_dict['player1_name'] = f"{t['p1_first_name']} {t['p1_last_name']}"
            team_dict['player2_name'] = f"{t['p2_first_name']} {t['p2_last_name']}"
            teams.append(team_dict)
        
        if not teams:
            return jsonify({"message": "No hay equipos globales de dobles registrados."}), 404 # 404 si no hay equipos
            
        return jsonify(teams), 200
    except sqlite3.Error as e:
        print(f"ERROR DB: [get_global_doubles_teams_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener equipos de dobles globales: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_global_doubles_teams_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener equipos de dobles globales: {str(e)}"}), 500

@app.route('/player_dashboard')
@login_required # Proteger este panel
def player_dashboard_page():
    # Si el usuario es admin, lo redirigimos a su panel principal para evitar confusiones.
    if session.get('is_admin'):
        flash('Acceso denegado. Eres un administrador. Usa el panel de organizador.', 'warning')
        return redirect(url_for('organizer_page'))
    
    user_id = session.get('user_id')
    db = get_db()
    
    # Intentar obtener el player_id vinculado al user_id actual
    linked_player = db.execute(
        "SELECT player_id FROM UserPlayersLink WHERE user_id = ?", (user_id,)
    ).fetchone()

    # Si no hay perfil de jugador vinculado, redirigir a completar perfil
    if not linked_player:
        flash('Por favor, completa tu perfil de jugador para acceder a tu dashboard.', 'info')
        return redirect(url_for('complete_player_profile')) # Asegúrate de que esta es la ruta de tu página
    
    player_id = linked_player['player_id']
    session['player_id'] = player_id # Asegurarse de que player_id esté en la sesión si no lo estaba ya.

    # Obtener solo la información básica del jugador para el template inicial
    # Se recuperan campos adicionales para que el JS pueda mostrarlos directamente.
    player_info = db.execute(
        '''SELECT 
            first_name, last_name, email, current_position, activity_status,
            activity_index_single, activity_status_single,
            activity_index_doubles, activity_status_doubles,
            rejections_current_cycle, rejections_total, last_activity_update
           FROM Players WHERE id = ?''', (player_id,)
    ).fetchone()

    if player_info:
        player_info_dict = dict(player_info) # Convertir a diccionario para fácil acceso en Jinja y JS
        # Formatear last_activity_update para una mejor visualización
        if player_info_dict['last_activity_update']:
            try:
                dt_object = datetime.strptime(player_info_dict['last_activity_update'], '%Y-%m-%d %H:%M:%S')
                player_info_dict['last_activity_update_formatted'] = dt_object.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                player_info_dict['last_activity_update_formatted'] = 'N/A'
        else:
            player_info_dict['last_activity_update_formatted'] = 'Nunca'

        player_full_name_for_greeting = f"{player_info_dict['first_name']} {player_info_dict['last_name']}"
    else:
        # Fallback si el perfil de jugador se desvinculó o eliminó inesperadamente
        flash('Tu perfil de jugador no fue encontrado. Contacta al administrador.', 'error')
        session.pop('player_id', None)
        return redirect(url_for('logout')) # O a una página de error

    return render_template('player_dashboard.html', 
                            user_username=session.get('username'),
                            user_id=str(session.get('user_id')), # Pasar como string para data-attribute
                            player_id=str(player_id),           # Pasar como string para data-attribute
                            player_is_linked=True, 
                            player_info=player_info_dict,
                            player_greeting_name=player_full_name_for_greeting) # Pasar el diccionario completo


@app.route('/complete_player_profile', methods=['GET', 'POST'])
@login_required
def complete_player_profile():
    user_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    # --- INICIO DE LOS DEBUG PARA COLUMNAS DE LA DB ---
    print("\n--- DEBUG: Información de la tabla Players desde la DB ---")
    try:
        cursor.execute("PRAGMA table_info(Players)")
        columns_info = cursor.fetchall()
        print(f"Total de columnas en la tabla Players (PRAGMA): {len(columns_info)}")
        print("Detalle de las columnas:")
        for col in columns_info:
            print(f"  Name: {col['name']}, Type: {col['type']}, NotNull: {col['notnull']}, DfltValue: {col['dflt_value']}, Pk: {col['pk']}")
    except Exception as e:
        print(f"ERROR DEBUG: No se pudo obtener la información de la tabla Players: {e}")
    print("--- FIN DEBUG ---")
    # --- FIN DE LOS DEBUG PARA COLUMNAS DE LA DB ---

    # Verificar si el usuario ya tiene un perfil de jugador vinculado
    linked_player = db.execute(
        "SELECT player_id FROM UserPlayersLink WHERE user_id = ?", (user_id,)
    ).fetchone()

    if request.method == 'POST':
        # --- Lógica para la petición POST (guardar perfil) ---
        if linked_player:
            flash('Tu cuenta ya tiene un perfil de jugador vinculado. Si deseas editarlo, usa la función de edición.', 'info')
            print("DEBUG POST /complete_player_profile: Perfil ya vinculado, devolviendo 400.")
            return jsonify({"error": "Perfil de jugador ya vinculado."}), 400

        try:
            # Extraer datos del formulario
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            gender = request.form.get('gender')
            birth_date = request.form.get('birth_date')
            location = request.form.get('location')
            dominant_hand = request.form.get('dominant_hand')
            backhand_type = request.form.get('backhand_type')
            racquet = request.form.get('racquet')
            
            # Validación básica en el servidor
            if not all([first_name, last_name, email, gender, birth_date]):
                flash('Nombre, Apellido, Email, Género y Fecha de Nacimiento son obligatorios.', 'error')
                print("DEBUG POST /complete_player_profile: Faltan campos obligatorios, devolviendo 400.")
                return jsonify({"error": "Faltan campos obligatorios."}), 400

            # Verificar que el email del formulario coincida con el email de la sesión
            session_email = session.get('email')
            if not session_email or email != session_email:
                flash('El email proporcionado no coincide con el email de tu cuenta de usuario o no está en sesión.', 'error')
                print("DEBUG POST /complete_player_profile: Inconsistencia de email, devolviendo 400.")
                return jsonify({"error": "Inconsistencia de email o email de sesión faltante."}), 400

            existing_player_to_link = db.execute(
                """SELECT p.id FROM Players p
                   LEFT JOIN UserPlayersLink upl ON p.id = upl.player_id
                   WHERE p.email = ? AND upl.player_id IS NULL""",
                (email,)
            ).fetchone()

            player_id_to_use = None

            if existing_player_to_link:
                # Esto es una ACTUALIZACIÓN si el jugador existe y NO está vinculado a otro usuario
                player_id_to_use = existing_player_to_link['id']
                cursor.execute(
                    """UPDATE Players SET
                        first_name = ?, last_name = ?, phone = ?, gender = ?, birth_date = ?,
                        location = ?, dominant_hand = ?, backhand_type = ?, racquet = ?,
                        last_activity_update = CURRENT_TIMESTAMP
                        WHERE id = ?""",
                    (first_name, last_name, phone, gender, birth_date, location,
                     dominant_hand, backhand_type, racquet, player_id_to_use)
                )
                flash_message_success = 'Perfil de jugador existente actualizado y vinculado exitosamente. ¡Bienvenido al torneo!'
                print(f"DEBUG POST /complete_player_profile: Usuario {session.get('username')} (ID: {user_id}) vinculado y actualizó Player {player_id_to_use} (existente).")

            else:
                # Esto es una INSERCIÓN de un nuevo jugador si no existe un perfil desvinculado con ese email
                existing_linked_player_with_email = db.execute(
                    """SELECT p.id FROM Players p
                       JOIN UserPlayersLink upl ON p.id = upl.player_id
                       WHERE p.email = ?""",
                    (email,)
                ).fetchone()

                if existing_linked_player_with_email:
                    flash('Este email ya está asociado a otro perfil de jugador en el sistema. Por favor, use un email diferente o contacte al organizador.', 'error')
                    print("DEBUG POST /complete_player_profile: Email de jugador ya en uso por otro perfil, devolviendo 409.")
                    return jsonify({"error": "Email de jugador ya en uso por otro perfil."}), 409

                # Manejar la subida de foto
                photo_filename = None
                if 'photo' in request.files:
                    file = request.files.get('photo')
                    if file and file.filename != '' and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = str(datetime.now().timestamp()).replace(".", "") + "_" + filename
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        print(f"DEBUG POST /complete_player_profile: Intentando guardar archivo en: {file_path}")
                        try:
                            file.save(file_path)
                            photo_filename = unique_filename
                            print(f"DEBUG POST /complete_player_profile: Archivo guardado exitosamente: {photo_filename}")
                        except Exception as file_save_error:
                            print(f"ERROR POST /complete_player_profile: Falló al guardar archivo: {file_save_error}")
                            flash(f"Error al guardar la foto: {file_save_error}", 'error')
                            return jsonify({"error": f"Error al guardar la foto: {file_save_error}"}), 500
                    elif file and file.filename == '':
                        print("DEBUG POST /complete_player_profile: Campo de foto presente pero vacío.")
                    else:
                        print("DEBUG POST /complete_player_profile: Archivo no permitido o no presente.")
                else:
                    print("DEBUG POST /complete_player_profile: Campo 'photo' no encontrado en request.files.")

                # Determinar la posición inicial
                last_pos_row = db.execute('SELECT MAX(current_position) as max_pos FROM Players').fetchone()
                initial_position = (last_pos_row['max_pos'] or 0) + 1
                current_position = initial_position
                points = 0

                # --- INICIO DE LA TUPLA Y CONSULTA SQL CORREGIDAS ---
                # Esta tupla ahora tiene 33 elementos, incluyendo 'None' para el ID
                valores_a_insertar = (
                    None, # ID (1)
                    first_name, last_name, email, None, phone, gender, # (2 a 7)
                    birth_date, location, dominant_hand, backhand_type, racquet, # (8 a 12)
                    photo_filename, initial_position, current_position, points, # (13 a 16)
                    0, 0, 0, 0, 0, 'rojo', # activity_index_single a activity_status_single (17 a 22)
                    0, 0, 0, 0, 0, 'rojo', # activity_index_doubles a activity_status_doubles (23 a 28)
                    0, 0, 'rojo', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None # rejections_current_cycle a last_challenge_received_date (29 a 33)
                    # <<--- LA COLUMNA 'registration_type' Y SU VALOR HAN SIDO ELIMINADOS DE AQUÍ
                )

                print(f"\n--- DEBUG FINAL: Información de la Tupla 'valores_a_insertar' ---")
                print(f"Cantidad de elementos en 'valores_a_insertar': {len(valores_a_insertar)}") # Debería imprimir 33
                print(f"Valores de 'valores_a_insertar': {valores_a_insertar}")
                print("--- FIN DEBUG FINAL ---")

                # Consulta SQL modificada: ¡NO ESPECIFICAMOS LAS COLUMNAS!
                # Confiamos en que la tupla de valores está en el orden correcto de las 33 columnas de la tabla.
                sql_insert_query = """INSERT INTO Players
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                # Asegúrate de que haya exactamente 33 placeholders '?' aquí.

                print(f"--- DEBUG FINAL: Información de la Consulta SQL de Inserción ---")
                print(f"Cantidad de placeholders '?' en la consulta SQL: {sql_insert_query.count('?')}") # Debería imprimir 33
                print(f"Texto de la consulta SQL:\n{sql_insert_query}")
                print("--- FIN DEBUG FINAL ---")

                # Ejecutar la inserción
                cursor.execute(sql_insert_query, valores_a_insertar)
                # --- FIN DE LA TUPLA Y CONSULTA SQL CORREGIDAS ---

                new_player_id = cursor.lastrowid
                player_id_to_use = new_player_id
                flash_message_success = 'Perfil de jugador creado y vinculado exitosamente. ¡Bienvenido al torneo!'
                print(f"DEBUG POST /complete_player_profile: Usuario {session.get('username')} (ID: {user_id}) creó y vinculó nuevo Player {player_id_to_use}.")

            # Crear enlace en UserPlayersLink table (esto es correcto aquí, aplica tanto para nueva creación como actualización)
            cursor.execute(
                "INSERT INTO UserPlayersLink (user_id, player_id) VALUES (?, ?)",
                (user_id, player_id_to_use)
            )
            db.commit()

            # Actualizar sesión con player_id
            session['player_id'] = player_id_to_use
            print(f"DEBUG POST /complete_player_profile: session['player_id'] actualizado a {session['player_id']}")
            flash(flash_message_success, 'success')
            print("DEBUG POST /complete_player_profile: Perfil guardado exitosamente, devolviendo 200 JSON.")
            return jsonify({"message": flash_message_success, "player_id": player_id_to_use}), 200

        except sqlite3.IntegrityError as e:
            db.rollback()
            if "UNIQUE constraint failed: UserPlayersLink.player_id" in str(e):
                flash('Este perfil de jugador ya está vinculado a otra cuenta de usuario.', 'error')
                print("DEBUG POST /complete_player_profile: Error de integridad (Player ya vinculado), devolviendo 409.")
                return jsonify({"error": "Perfil de jugador ya vinculado a otra cuenta."}), 409
            elif "UNIQUE constraint failed: Players.email" in str(e):
                flash('Este email ya está registrado para otro jugador. Por favor, use un email diferente o contacte al organizador.', 'error')
                print("DEBUG POST /complete_player_profile: Error de integridad (Email de Player ya existe), devolviendo 409.")
                return jsonify({"error": "Email de jugador ya existe."}), 409
            flash(f"Error de base de datos (Integridad): {e}", 'error')
            print(f"ERROR DB (Integrity): [complete_player_profile_post] {e}")
            return jsonify({"error": "Error de integridad de base de datos."}), 500
        except sqlite3.Error as e:
            db.rollback()
            flash(f"Error de base de datos: {e}", 'error')
            print(f"ERROR DB: [complete_player_profile_post] {e}")
            return jsonify({"error": "Error de base de datos."}), 500
        except Exception as e:
            db.rollback()
            flash(f"Error inesperado al guardar el perfil: {e}", 'error')
            print(f"ERROR GENERICO: [complete_player_profile_post] {e}")
            return jsonify({"error": "Error inesperado."}), 500

    else: # request.method == 'GET'
        # --- Lógica para la petición GET (renderizar formulario) ---
        if linked_player:
            # Si ya tiene un perfil, redirigirlo a su dashboard
            flash('Tu cuenta ya tiene un perfil de jugador vinculado. Si deseas editarlo, usa la función de edición.', 'info')
            return redirect(url_for('player_dashboard_page'))

        # Si no tiene perfil, renderizar el formulario para completarlo
        user_email = session.get('email')
        return render_template('complete_player_profile.html', user_email=user_email)

@app.route('/register_for_tournament', methods=['POST'])
@login_required
def register_for_tournament():
    user_id = session.get('user_id')
    player_id = session.get('player_id') # Asegurarse de que el usuario tiene un perfil de jugador vinculado

    if not player_id:
        flash('Debes completar tu perfil de jugador antes de inscribirte a un torneo.', 'error')
        return jsonify({"error": "Perfil de jugador incompleto."}), 400

    tournament_id = request.json.get('tournament_id') # Esperamos un JSON para este POST

    if not tournament_id:
        return jsonify({"error": "ID de torneo no proporcionado."}), 400

    db = get_db()
    cursor = db.cursor()

    try:
        # 1. Verificar que el torneo exista y esté publicado
        tournament = db.execute(
            "SELECT * FROM Tournaments WHERE id = ? AND is_published = 1", (tournament_id,)
        ).fetchone()

        if not tournament:
            return jsonify({"error": "Torneo no encontrado o no disponible para inscripción."}), 404

        # 2. Verificar que el torneo esté en fase de inscripción abierta
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not (tournament['registration_start_date'] <= current_time <= tournament['registration_end_date']):
            return jsonify({"error": "Las inscripciones para este torneo no están abiertas en este momento."}), 400

        # 3. Verificar si el jugador ya está inscrito
        existing_registration = db.execute(
            "SELECT id FROM TournamentRegistrations WHERE player_id = ? AND tournament_id = ?",
            (player_id, tournament_id)
        ).fetchone()

        if existing_registration:
            return jsonify({"error": "Ya estás inscrito en este torneo."}), 409

        # 4. Verificar cupos máximos (si max_slots > 0)
        if tournament['max_slots'] > 0:
            current_registrations = db.execute(
                "SELECT COUNT(id) FROM TournamentRegistrations WHERE tournament_id = ? AND status = 'inscrito'",
                (tournament_id,)
            ).fetchone()[0]
            if current_registrations >= tournament['max_slots']:
                return jsonify({"error": "Este torneo ha alcanzado su límite de inscripciones."}), 400

        # 5. Realizar la inscripción
        cursor.execute(
            "INSERT INTO TournamentRegistrations (player_id, tournament_id, registration_date, status) VALUES (?, ?, ?, ?)",
            (player_id, tournament_id, current_time, 'inscrito')
        )
        db.commit()

        flash('Te has inscrito exitosamente en el torneo: ' + tournament['name'], 'success')
        return jsonify({"message": "Inscripción exitosa.", "tournament_name": tournament['name']}), 200

    except sqlite3.IntegrityError as e:
        db.rollback()
        return jsonify({"error": f"Error de base de datos (Integridad): {e}"}), 500
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({"error": f"Error de base de datos: {e}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO en register_for_tournament: {e}")
        return jsonify({"error": f"Error inesperado: {e}"}), 500



# app.py

# AHORA, PEGA LA FUNCIÓN request_doubles_partner_api AQUÍ DEBAJO:
@app.route('/api/doubles/request_partner_v2', methods=['POST'])
@login_required
def request_doubles_partner_api():
    print("DEBUG: ¡¡¡request_doubles_partner_api_V2 EJECUTÁNDOSE!!!")
    user_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()
    
    linked_player_row = db.execute(
        "SELECT player_id FROM UserPlayersLink WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not linked_player_row:
        return jsonify({"error": "Tu cuenta no está vinculada a un perfil de jugador."}), 400
    
    requester_player_id = linked_player_row['player_id']

    data = request.get_json()
    requested_player_id = data.get('requested_player_id')
    tournament_id = data.get('tournament_id')

    if not requested_player_id or not tournament_id:
        return jsonify({"error": "Se requiere el ID del jugador solicitado y el ID del torneo."}), 400

    if requester_player_id == requested_player_id:
        return jsonify({"error": "No puedes enviarte una solicitud a ti mismo."}), 400

    try:
        # 1. Verificar que el torneo exista y sea de dobles
        tournament = db.execute("SELECT id, type FROM Tournaments WHERE id = ?", (tournament_id,)).fetchone()
        if not tournament:
            return jsonify({"error": "Torneo no encontrado."}), 404
        if not tournament['type'].startswith('pyramid_doubles_') and not tournament['type'].startswith('satellite_doubles_'):
            return jsonify({"error": "El torneo seleccionado no es un torneo de dobles."}), 400

        # 2. Validar elegibilidad del jugador solicitado *para este torneo*
        requested_player_data = db.execute(
            '''
            SELECT p.id, p.first_name, p.last_name, p.gender
            FROM Players p
            LEFT JOIN TournamentTeams tt ON (
                (p.id = (SELECT player1_id FROM Teams WHERE id = tt.team_id)) OR
                (p.id = (SELECT player2_id FROM Teams WHERE id = tt.team_id))
            ) AND tt.tournament_id = ?
            WHERE p.id = ? AND tt.id IS NULL
            ''',
            (tournament_id, requested_player_id)
        ).fetchone()

        if not requested_player_data:
            return jsonify({"error": "El jugador solicitado no es elegible para este torneo (quizás ya está en un equipo para este torneo)."}), 400

        # 3. Verificar que el solicitante NO esté ya en un equipo para ESTE torneo
        requester_in_team_for_tournament = db.execute(
            '''
            SELECT tt.id FROM TournamentTeams tt
            JOIN Teams t ON tt.team_id = t.id
            WHERE tt.tournament_id = ? AND (t.player1_id = ? OR t.player2_id = ?)
            ''',
            (tournament_id, requester_player_id, requester_player_id)
        ).fetchone()

        if requester_in_team_for_tournament:
            return jsonify({"error": "Ya estás en un equipo para este torneo."}), 409

        # 4. Verificar si ya existe una solicitud pendiente entre estos dos jugadores PARA ESTE TORNEO (en cualquier dirección)
        existing_request = db.execute(
            '''SELECT id FROM DoublesPartnerRequests
               WHERE tournament_id = ?
                 AND ((requester_player_id = ? AND requested_player_id = ?)
                  OR (requester_player_id = ? AND requested_player_id = ?))
                 AND status = 'pending' ''',
            (tournament_id, requester_player_id, requested_player_id, requested_player_id, requester_player_id)
        ).fetchone()

        if existing_request:
            return jsonify({"error": "Ya existe una solicitud pendiente con este jugador para este torneo."}), 409

        # 5. Insertar la nueva solicitud de compañero (ahora con tournament_id)
        cursor.execute(
            """INSERT INTO DoublesPartnerRequests (tournament_id, requester_player_id, requested_player_id, status)
               VALUES (?, ?, ?, ?)""",
            (tournament_id, requester_player_id, requested_player_id, 'pending')
        )
        db.commit()

        return jsonify({"message": "Solicitud de compañero enviada exitosamente para el torneo."}), 201

    except sqlite3.IntegrityError as e:
        db.rollback()
        print(f"ERROR DB: [request_doubles_partner_api] Error de SQLite (Integridad): {str(e)}")
        traceback.print_exc()
        # --- CAMBIO AQUÍ: RELANZAR LA EXCEPCIÓN EN MODO DEBUG ---
        if app.debug: # Solo relanzar si Flask está en modo debug
            raise e
        # --- FIN CAMBIO ---
        return jsonify({"error": f"Error de base de datos (Integridad): {str(e)}"}), 500
    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [request_doubles_partner_api] Error de SQLite: {str(e)}")
        traceback.print_exc()
        # --- CAMBIO AQUÍ: RELANZAR LA EXCEPCIÓN EN MODO DEBUG ---
        if app.debug:
            raise e
        # --- FIN CAMBIO ---
        return jsonify({"error": f"Error de base de datos al enviar solicitud: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [request_doubles_partner_api] Error inesperado: {str(e)}")
        traceback.print_exc()
        # --- CAMBIO AQUÍ: RELANZAR LA EXCEPCIÓN EN MODO DEBUG ---
        if app.debug:
            raise e
        # --- FIN CAMBIO ---
        return jsonify({"error": f"Error inesperado al enviar solicitud: {str(e)}"}), 500


@app.route('/api/doubles/my_partner_requests', methods=['GET'])
@login_required
def get_my_partner_requests_api():
    user_id = session.get('user_id')
    db = get_db()

    linked_player_row = db.execute(
        "SELECT player_id FROM UserPlayersLink WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not linked_player_row:
        return jsonify({"error": "Tu cuenta no está vinculada a un perfil de jugador."}), 400
    
    current_player_id = linked_player_row['player_id']

    try:
        # Solicitudes ENVIADAS por el jugador actual
        sent_requests_db = db.execute(
            '''SELECT dpr.id, dpr.requested_player_id, dpr.status, dpr.created_at, dpr.tournament_id,
                      p.first_name || ' ' || p.last_name AS requested_player_name,
                      t.name AS tournament_name -- <<-- Obtener el nombre del torneo
               FROM DoublesPartnerRequests dpr
               JOIN Players p ON dpr.requested_player_id = p.id
               JOIN Tournaments t ON dpr.tournament_id = t.id -- <<-- Unir con Tournaments
               WHERE dpr.requester_player_id = ?
               ORDER BY dpr.created_at DESC''',
            (current_player_id,)
        ).fetchall()
        
        sent_requests = [dict(req) for req in sent_requests_db]

        # Solicitudes RECIBIDAS por el jugador actual
        received_requests_db = db.execute(
            '''SELECT dpr.id, dpr.requester_player_id, dpr.status, dpr.created_at, dpr.tournament_id,
                      p.first_name || ' ' || p.last_name AS requester_player_name,
                      t.name AS tournament_name -- <<-- Obtener el nombre del torneo
               FROM DoublesPartnerRequests dpr
               JOIN Players p ON dpr.requester_player_id = p.id
               JOIN Tournaments t ON dpr.tournament_id = t.id -- <<-- Unir con Tournaments
               WHERE dpr.requested_player_id = ?
               ORDER BY dpr.created_at DESC''',
            (current_player_id,)
        ).fetchall()

        received_requests = [dict(req) for req in received_requests_db]

        return jsonify({
            "sent_requests": sent_requests,
            "received_requests": received_requests
        }), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_my_partner_requests_api] Error de SQLite: {str(e)}")
        return jsonify({"error": f"Error de base de datos al obtener solicitudes de compañero: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [get_my_partner_requests_api] Error inesperado: {str(e)}")
        return jsonify({"error": f"Error inesperado al obtener solicitudes de compañero: {str(e)}"}), 500

@app.route('/api/doubles/respond_partner_request/<int:request_id>', methods=['POST'])
@login_required
def respond_partner_request_api(request_id):
    print("DEBUG: ¡¡¡request_doubles_partner_api_V2 EJECUTÁNDOSE!!!")
    user_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()
    
    linked_player_row = db.execute(
        "SELECT player_id FROM UserPlayersLink WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not linked_player_row:
        return jsonify({"error": "Tu cuenta no está vinculada a un perfil de jugador."}), 400
    
    current_player_id = linked_player_row['player_id']

    data = request.get_json()
    # --- ¡CAMBIO AQUI! Extraer 'action' del JSON ---
    action = data.get('action') # 'accept' o 'reject'
    # --- FIN CAMBIO ---

    # Validar que 'action' sea válida antes de continuar
    if action not in ['accept', 'reject']:
        return jsonify({"error": "Acción no válida. Debe ser 'accept' o 'reject'."}), 400

    try:
        # Obtener la solicitud (incluye tournament_id)
        request_data = db.execute(
            "SELECT requester_player_id, requested_player_id, status, tournament_id FROM DoublesPartnerRequests WHERE id = ?",
            (request_id,)
        ).fetchone()

        if not request_data:
            return jsonify({"error": "Solicitud no encontrada."}), 404

        # Verificar que el jugador actual tiene permiso para responder esta solicitud
        if request_data['requested_player_id'] != current_player_id:
            return jsonify({"error": "No tienes permiso para responder a esta solicitud."}), 403 # Forbidden

        if request_data['status'] != 'pending':
            return jsonify({"error": "Esta solicitud ya no está pendiente."}), 400
        
        requester_id = request_data['requester_player_id']
        requested_id = request_data['requested_player_id']
        tournament_id = request_data['tournament_id'] # Obtener tournament_id de la solicitud

        if action == 'accept':
            # 1. Verificar si alguno de los jugadores ya está en un equipo *para ESTE torneo*
            for player_check_id in [requester_id, requested_id]:
                existing_team_for_player = db.execute(
                    '''SELECT tt.id, t.team_name FROM TournamentTeams tt
                       JOIN Teams t ON tt.team_id = t.id
                       WHERE tt.tournament_id = ? AND (t.player1_id = ? OR t.player2_id = ?)''',
                    (tournament_id, player_check_id, player_check_id)
                ).fetchone()
                if existing_team_for_player:
                    # Si ya está en un equipo, rechazar la solicitud actual y notificar
                    cursor.execute("UPDATE DoublesPartnerRequests SET status = 'rejected' WHERE id = ?", (request_id,))
                    db.commit()
                    return jsonify({"error": f"No se pudo aceptar: Jugador {player_check_id} ya está en el equipo '{existing_team_for_player['team_name']}' para este torneo."}), 409

            # 2. Obtener el género de los jugadores (de Players global)
            requester_gender = db.execute('SELECT gender FROM Players WHERE id = ?', (requester_id,)).fetchone()['gender']
            requested_gender = db.execute('SELECT gender FROM Players WHERE id = ?', (requested_id,)).fetchone()['gender']

            if requester_gender != requested_gender:
                cursor.execute("UPDATE DoublesPartnerRequests SET status = 'rejected' WHERE id = ?", (request_id,))
                db.commit()
                return jsonify({"error": "No se pudo formar el equipo: los jugadores no son del mismo género."}), 400

            # 3. Formar el Equipo GLOBAL si no existe (en la tabla Teams)
            existing_global_team = db.execute(
                '''SELECT id FROM Teams WHERE
                   (player1_id = ? AND player2_id = ?) OR (player1_id = ? AND player2_id = ?)''',
                (requester_id, requested_id, requested_id, requester_id)
            ).fetchone()

            global_team_id = None
            if existing_global_team:
                global_team_id = existing_global_team['id']
                print(f"DEBUG: Equipo global ya existente (ID: {global_team_id}).")
            else:
                team_name = f"{db.execute('SELECT first_name FROM Players WHERE id = ?', (requester_id,)).fetchone()['first_name']}/{db.execute('SELECT first_name FROM Players WHERE id = ?', (requested_id,)).fetchone()['first_name']}"
                gender_category = requester_gender

                cursor.execute(
                    """INSERT INTO Teams (player1_id, player2_id, team_name, gender_category)
                       VALUES (?, ?, ?, ?)""",
                    (requester_id, requested_id, team_name, gender_category)
                )
                global_team_id = cursor.lastrowid
                print(f"DEBUG: Nuevo equipo global creado (ID: {global_team_id}).")

            # 4. Registrar el equipo en TournamentTeams para ESTE TORNEO
            tournament_type_info = db.execute("SELECT type FROM Tournaments WHERE id = ?", (tournament_id,)).fetchone()
            if not tournament_type_info:
                return jsonify({"error": "Información del torneo no encontrada para registro de equipo."}), 500

            is_pyramid_doubles_tournament = tournament_type_info['type'].startswith('pyramid_doubles_')

            tournament_team_initial_pos = 0
            tournament_team_current_pos = 0

            if is_pyramid_doubles_tournament:
                last_tournament_team_pos_row = db.execute(
                    '''SELECT MAX(tournament_current_position) as max_pos FROM TournamentTeams
                       WHERE tournament_id = ?''',
                    (tournament_id,)
                ).fetchone()
                tournament_team_initial_pos = (last_tournament_team_pos_row['max_pos'] or 0) + 1
                tournament_team_current_pos = tournament_team_initial_pos
            else:
                tournament_team_initial_pos = 1
                tournament_team_current_pos = 1

            cursor.execute(
                """INSERT INTO TournamentTeams (tournament_id, team_id, tournament_initial_position, tournament_current_position)
                   VALUES (?, ?, ?, ?)""",
                (tournament_id, global_team_id, tournament_team_initial_pos, tournament_team_current_pos)
            )

            # 5. Marcar la solicitud como aceptada
            cursor.execute("UPDATE DoublesPartnerRequests SET status = 'accepted' WHERE id = ?", (request_id,))

            # 6. Opcional: Rechazar automáticamente otras solicitudes pendientes para ambos jugadores *para este torneo*
            cursor.execute(
                """UPDATE DoublesPartnerRequests SET status = 'rejected'
                   WHERE status = 'pending' AND tournament_id = ?
                     AND (requester_player_id = ? OR requested_player_id = ? OR requester_player_id = ? OR requested_player_id = ?)""",
                (tournament_id, requester_id, requester_id, requested_id, requested_id)
            )

            db.commit()
            return jsonify({"message": f"Solicitud aceptada. Se ha formado el equipo '{team_name}' y se ha registrado para el torneo."}), 200

        elif action == 'reject':
            cursor.execute("UPDATE DoublesPartnerRequests SET status = 'rejected' WHERE id = ?", (request_id,))
            db.commit()
            return jsonify({"message": "Solicitud rechazada."}), 200

    except sqlite3.IntegrityError as e:
        db.rollback()
        print(f"ERROR DB: [respond_partner_request_api] Error de SQLite (Integridad): {str(e)}")
        traceback.print_exc()
        if app.debug: raise e
        return jsonify({"error": f"Error de base de datos (Integridad): {str(e)}"}), 500
    except sqlite3.Error as e:
        db.rollback()
        print(f"ERROR DB: [respond_partner_request_api] Error de SQLite: {str(e)}")
        traceback.print_exc()
        if app.debug: raise e
        return jsonify({"error": f"Error de base de datos al responder solicitud: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        print(f"ERROR GENERICO: [respond_partner_request_api] Error inesperado: {str(e)}")
        traceback.print_exc()
        if app.debug: raise e
        return jsonify({"error": f"Error inesperado al responder solicitud: {str(e)}"}), 500
    
@app.route('/api/doubles/my_global_teams', methods=['GET'])
@login_required
def get_my_global_teams_api():
    user_id = session.get('user_id')
    player_id = session.get('player_id')

    if not player_id:
        return jsonify({"error": "No hay un perfil de jugador vinculado a tu cuenta."}), 400

    db = get_db()

    gender_category_filter = request.args.get('gender_category') # Ej: 'Masculino', 'Femenino', 'Mixto'

    try:
        query = '''
            SELECT t.id, t.team_name, t.player1_id, t.player2_id, t.gender_category,
                    p1.first_name AS p1_first_name, p1.last_name AS p1_last_name,
                    p2.first_name AS p2_first_name, p2.last_name AS p2_last_name
            FROM Teams t
            JOIN Players p1 ON t.player1_id = p1.id
            JOIN Players p2 ON t.player2_id = p2.id
            WHERE (t.player1_id = ? OR t.player2_id = ?)
        '''
        params = [player_id, player_id]

        if gender_category_filter:
            query += " AND t.gender_category = ?"
            params.append(gender_category_filter)
        
        query += " ORDER BY t.team_name ASC"

        teams_db = db.execute(query, params).fetchall()

        teams_list = []
        for team_row in teams_db:
            team_dict = dict(team_row)
            team_dict['player1_name'] = f"{team_row['p1_first_name']} {team_row['p1_last_name']}"
            team_dict['player2_name'] = f"{team_row['p2_first_name']} {team_row['p2_last_name']}"
            teams_list.append(team_dict)
        
        return jsonify(teams_list), 200

    except sqlite3.Error as e:
        print(f"ERROR DB: [get_my_global_teams_api] Error de SQLite: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Error de base de datos al obtener equipos globales: {str(e)}"}), 500
    except Exception as e:
        print(f"ERROR GENERICO: [get_my_global_teams_api] Error inesperado: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Error inesperado al obtener equipos globales: {str(e)}"}), 500

# --- Punto de Entrada de la Aplicación ---
if __name__ == '__main__':
    with app.app_context():
        init_db()
        create_initial_admin() # Llama a la función para crear el admin
    app.run(debug=False)
