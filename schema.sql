-- schema.sql - Versión Reestructurada para Múltiples Torneos y Ranking Híbrido

-- Elimina TODAS las tablas si ya existen para un reinicio limpio
DROP TABLE IF EXISTS ActivityLog;
DROP TABLE IF EXISTS DoublesPartnerRequests;
DROP TABLE IF EXISTS DoublesMatches;
DROP TABLE IF EXISTS TournamentTeams; -- Nueva tabla
DROP TABLE IF EXISTS Teams; -- Modificada
DROP TABLE IF EXISTS Challenges;
DROP TABLE IF EXISTS Matches; -- Modificada
DROP TABLE IF EXISTS TournamentPlayers; -- Nueva tabla
DROP TABLE IF EXISTS TournamentRegistrations; -- Nueva tabla
DROP TABLE IF EXISTS Tournaments; -- Nueva tabla
DROP TABLE IF EXISTS UserPlayersLink; -- Modificada
DROP TABLE IF EXISTS Users; -- Modificada
DROP TABLE IF EXISTS Players; -- Modificada
DROP TABLE IF EXISTS TournamentSettings;


CREATE TABLE IF NOT EXISTS Tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    registration_start_date DATETIME, -- AÑADIDA
    registration_end_date DATETIME,   -- AÑADIDA
    type TEXT NOT NULL,               -- AÑADIDA (ej. 'pyramid_single', 'satellite_single')
    status TEXT NOT NULL DEFAULT 'registration_open', -- AÑADIDA
    description TEXT,
    rules_url TEXT,                   -- ESTABA ANTES
    is_active INTEGER DEFAULT 0,      -- ESTABA ANTES (o lo que tengas)
    is_published INTEGER DEFAULT 0,   -- AÑADIDA
    category TEXT DEFAULT '',       -- Asegura un DEFAULT vacío si no hay valor
    max_slots INTEGER DEFAULT 0,    -- Asegura un DEFAULT
    cost REAL DEFAULT 0.0,          -- Asegura un DEFAULT
    requirements TEXT DEFAULT '',   -- Asegura un DEFAULT
    location TEXT DEFAULT '',       -- Asegura un DEFAULT
    organizer_id INTEGER NOT NULL, -- <<--- ¡Asegúrate de que esta línea esté presente!
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organizer_id) REFERENCES Users(id) -- <<--- ¡Y esta línea para la clave foránea!
);

-- Nueva tabla para las inscripciones de jugadores a torneos (Paso 4.1.2)
CREATE TABLE IF NOT EXISTS TournamentRegistrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL, -- <-- ¡Aquí está el cambio de user_id a player_id!
    tournament_id INTEGER NOT NULL,
    registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'inscrito',
    UNIQUE(player_id, tournament_id),
    FOREIGN KEY (player_id) REFERENCES Players(id),
    FOREIGN KEY (tournament_id) REFERENCES Tournaments(id)
);

-- 2. Tabla de Jugadores (Ranking Maestro General) - Modificada
CREATE TABLE IF NOT EXISTS Players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT, -- Puede ser NULL si el jugador no tiene cuenta de User vinculada
    phone TEXT,
    gender TEXT,
    birth_date TEXT,
    location TEXT,
    dominant_hand TEXT,
    backhand_type TEXT,
    racquet TEXT,
    photo_url TEXT,
    -- Columnas de ranking maestro y actividad global (solo afectadas por torneos tipo 'pyramid')
    initial_position INTEGER NOT NULL,
    current_position INTEGER NOT NULL,
    points INTEGER DEFAULT 0,
    
    activity_index_single INTEGER DEFAULT 0,
    challenges_emitted_single INTEGER DEFAULT 0,
    challenges_accepted_single INTEGER DEFAULT 0,
    challenges_won_single INTEGER DEFAULT 0,
    defenses_successful_single INTEGER DEFAULT 0,
    activity_status_single TEXT DEFAULT 'rojo',

    activity_index_doubles INTEGER DEFAULT 0,
    challenges_emitted_doubles INTEGER DEFAULT 0,
    challenges_accepted_doubles INTEGER DEFAULT 0,
    challenges_won_doubles INTEGER DEFAULT 0,
    defenses_successful_doubles INTEGER DEFAULT 0,
    activity_status_doubles TEXT DEFAULT 'rojo',

    rejections_current_cycle INTEGER DEFAULT 0,
    rejections_total INTEGER DEFAULT 0,
    activity_status TEXT DEFAULT 'rojo',
    last_activity_update DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_challenge_received_date DATETIME DEFAULT NULL
    
    
);

-- 4. Tabla de Partidos (Individuales) - Modificada
CREATE TABLE Matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL, -- NUEVO: A qué torneo pertenece este partido
    date TEXT NOT NULL,
    challenger_id INTEGER NOT NULL,
    challenged_id INTEGER NOT NULL,
    winner_id INTEGER NOT NULL,
    loser_id INTEGER NOT NULL,
    score_text TEXT NOT NULL,
    is_challenger_winner BOOLEAN NOT NULL,
    positions_swapped BOOLEAN NOT NULL,
    status TEXT NOT NULL DEFAULT 'valid',
    FOREIGN KEY (tournament_id) REFERENCES Tournaments (id),
    FOREIGN KEY (challenger_id) REFERENCES Players (id),
    FOREIGN KEY (challenged_id) REFERENCES Players (id),
    FOREIGN KEY (winner_id) REFERENCES Players (id),
    FOREIGN KEY (loser_id) REFERENCES Players (id)
);

-- 5. Tabla de Desafíos Pendientes (Individuales) - Modificada
CREATE TABLE IF NOT EXISTS Challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL, -- NUEVO: A qué torneo pertenece este desafío
    challenger_id INTEGER NOT NULL,
    challenged_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'played', 'cancelled', 'rejected', 'ignored'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    scheduled_date TEXT,
    FOREIGN KEY (tournament_id) REFERENCES Tournaments (id),
    FOREIGN KEY (challenger_id) REFERENCES Players(id),
    FOREIGN KEY (challenged_id) REFERENCES Players(id)
);

-- 6. Tabla para Equipos de Dobles (Definición Global de la Pareja) - Modificada
CREATE TABLE IF NOT EXISTS Teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_id INTEGER NOT NULL,
    player2_id INTEGER NOT NULL,
    team_name TEXT NOT NULL,
    gender_category TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- ¡NUEVAS COLUMNAS AGREGADAS! (para el ranking global de equipos, si lo necesitas)
    initial_position INTEGER, -- Puede ser NULL, o si es NOT NULL, dale un DEFAULT
    current_position INTEGER, -- Puede ser NULL, o si es NOT NULL, dale un DEFAULT
    -- Por ahora, haremos que puedan ser NULL. Si las necesitas NOT NULL, deberás darlas en los INSERT.

    FOREIGN KEY (player1_id) REFERENCES Players(id),
    FOREIGN KEY (player2_id) REFERENCES Players(id),
    UNIQUE (player1_id, player2_id) -- La misma pareja global solo puede existir una vez aquí
);

-- 7. Tabla de Ranking y Actividad de Equipos POR TORNEO (TournamentTeams) - NUEVA
CREATE TABLE IF NOT EXISTS TournamentTeams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL, -- Se refiere al Teams.id de la pareja global
    tournament_current_position INTEGER NOT NULL,
    tournament_initial_position INTEGER NOT NULL,
    tournament_points INTEGER DEFAULT 0,
    
    activity_index_team_doubles INTEGER DEFAULT 0,
    challenges_emitted_team_doubles INTEGER DEFAULT 0,
    challenges_accepted_team_doubles INTEGER DEFAULT 0,
    challenges_won_team_doubles INTEGER DEFAULT 0,
    defenses_successful_team_doubles INTEGER DEFAULT 0,
    rejections_team_doubles_current_cycle INTEGER DEFAULT 0,
    rejections_team_doubles_total INTEGER DEFAULT 0,
    activity_status_team_doubles TEXT DEFAULT 'rojo',
    last_activity_team_doubles_update DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tournament_id) REFERENCES Tournaments(id),
    FOREIGN KEY (team_id) REFERENCES Teams(id),
    UNIQUE (tournament_id, team_id) -- Un equipo global solo puede tener un ranking por torneo
);

-- 8. Tabla para Partidos de Dobles - Modificada
CREATE TABLE IF NOT EXISTS DoublesMatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL, -- NUEVO: A qué torneo pertenece este partido
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    team_a_id INTEGER NOT NULL,
    team_b_id INTEGER NOT NULL,
    winner_team_id INTEGER,
    loser_team_id INTEGER,
    score_text TEXT,
    is_team_a_winner INTEGER,
    positions_swapped INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tournament_id) REFERENCES Tournaments (id),
    FOREIGN KEY (team_a_id) REFERENCES TournamentTeams(id), -- REFERENCIA A TournamentTeams
    FOREIGN KEY (team_b_id) REFERENCES TournamentTeams(id), -- REFERENCIA A TournamentTeams
    FOREIGN KEY (winner_team_id) REFERENCES TournamentTeams(id), -- REFERENCIA A TournamentTeams
    FOREIGN KEY (loser_team_id) REFERENCES TournamentTeams(id) -- REFERENCIA A TournamentTeams
);


-- 9. NUEVA TABLA: DoublesPartnerRequests (Modificada para incluir tournament_id)
CREATE TABLE IF NOT EXISTS DoublesPartnerRequests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL, -- <<-- ¡Debe ser NOT NULL!
    requester_player_id INTEGER NOT NULL,
    requested_player_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'accepted', 'rejected', 'cancelled'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tournament_id) REFERENCES Tournaments(id),
    FOREIGN KEY (requester_player_id) REFERENCES Players(id),
    FOREIGN KEY (requested_player_id) REFERENCES Players(id),
    UNIQUE (tournament_id, requester_player_id, requested_player_id) -- <<-- ¡UNIQUE constraint debe incluir tournament_id!
);

-- 10. Tabla ActivityLog (se mantiene, pero las FK se actualizarán según el contexto de torneo/jugador global)
CREATE TABLE IF NOT EXISTS ActivityLog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    challenge_id INTEGER,
    match_id INTEGER,
    doubles_match_id INTEGER,
    tournament_id INTEGER, -- NUEVO: para registrar a qué torneo pertenece la actividad
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES Players(id),
    FOREIGN KEY (challenge_id) REFERENCES Challenges(id),
    FOREIGN KEY (match_id) REFERENCES Matches(id),
    FOREIGN KEY (doubles_match_id) REFERENCES DoublesMatches(id),
    FOREIGN KEY (tournament_id) REFERENCES Tournaments(id)
);

-- 11. Tabla TournamentSettings (se mantiene)
CREATE TABLE IF NOT EXISTS TournamentSettings (
    setting_name TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL
);

-- Insertar configuración inicial del ciclo (10 días)
INSERT OR IGNORE INTO TournamentSettings (setting_name, setting_value) VALUES
('cycle_duration_days', '10'),
('cycle_start_date', STRFTIME('%Y-%m-%d %H:%M:%S', 'now', 'start of day'));
-- NUEVO: Podríamos añadir un setting para el torneo_id_activo_actual

-- 12. Tabla de Usuarios (se mantiene, pero ahora UserPlayersLink se encarga de la vinculación)
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    email TEXT UNIQUE -- Usado para login y para posible vinculación automática a Player
);

-- 13. Tabla de Vinculación User-Player (se mantiene)
CREATE TABLE IF NOT EXISTS UserPlayersLink (
    user_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL UNIQUE,
    PRIMARY KEY (user_id, player_id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (player_id) REFERENCES Players(id)
);


-- Inserts para USUARIOS DE PRUEBA
-- ¡REEMPLAZA 'TU_HASH_GENERADO_AQUI' con los hashes que obtuviste en el Paso 1!
INSERT OR IGNORE INTO Users (id, username, password_hash, is_admin, email) VALUES
(100, 'admin_test', ' scrypt:32768:8:1$9bPnK5sWMlLj64bY$619d67b567f25370d1196b3d81f2cef943f28ce44d922b8cbb281d2a915234153460df14ea3c659de31ffa6f81d7910434a90b657d9e231cfdd13a9db084e232', 1, 'admin_test@example.com'), -- Admin de prueba
(101, 'jugador1_test', 'scrypt:32768:8:1$ZHG4sb67O1E51CAq$4b80481aa2b042dae78c1d318700b4fc0c50c81e199f358e2f2ce69e3edf96a8691f86ff5f5e5b9ad91529fd4664ff6c65a4d3f3c33b40b7bd26ea2e5d1c4e53', 0, 'jugador1_test@example.com'), -- Jugador normal 1
(102, 'jugador2_test', 'scrypt:32768:8:1$bJfb6pvfMmF61bpM$cc5a5fb64659e3217d286c942dbdb7ee993606c72030f08bd13e46b6b46fd2d1b55da3fe7f989c1db79e89dcd79f4f18de939fd7a1e964aaab74db62968fee1f', 0, 'jugador2_test@example.com'); -- Jugador normal 2

-- Inserts para PERFILES DE JUGADOR DE PRUEBA (correspondiendo a los usuarios de arriba)
-- Asegúrate de que las columnas coincidan con tu CREATE TABLE Players (33 columnas)
-- El 'id' aquí debe ser el mismo que el 'id' del usuario al que se vincula para UserPlayersLink
INSERT INTO Players (
    id, first_name, last_name, email, password_hash, phone, gender, birth_date,
    location, dominant_hand, backhand_type, racquet, photo_url,
    initial_position, current_position, points,
    activity_index_single, challenges_emitted_single, challenges_accepted_single, challenges_won_single, defenses_successful_single, activity_status_single,
    activity_index_doubles, challenges_emitted_doubles, challenges_accepted_doubles, challenges_won_doubles, defenses_successful_doubles, activity_status_doubles,
    rejections_current_cycle, rejections_total, activity_status, last_activity_update, last_challenge_received_date
) VALUES
(100, 'Admin', 'Test', 'admin_test@example.com', NULL, '111111111', 'Masculino', '1980-01-01', 'Ciudad', 'Derecha', 'Dos manos', 'TestRacquet', NULL, 1, 1, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(101, 'JugadorUno', 'Prueba', 'jugador1_test@example.com', NULL, '222222222', 'Masculino', '1990-05-15', 'Ciudad', 'Derecha', 'Una mano', 'TestRacquet', NULL, 2, 2, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(102, 'JugadorDos', 'Prueba', 'jugador2_test@example.com', NULL, '333333333', 'Masculino', '1991-03-20', 'Ciudad', 'Derecha', 'Dos manos', 'TestRacquet', NULL, 3, 3, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL);


-- Inserts para VINCULAR USUARIOS Y JUGADORES DE PRUEBA
INSERT INTO UserPlayersLink (user_id, player_id) VALUES
(100, 100), -- Vincula admin_test con su perfil de jugador
(101, 101), -- Vincula jugador1_test con su perfil de jugador
(102, 102); -- Vincula jugador2_test con su perfil de jugador

-- ... (resto de tus INSERTs de ejemplo para Tournaments, Teams, etc.) ...


-- DATOS INICIALES DE EJEMPLO PARA PLAYERS (¡MUY IMPORTANTE ACTUALIZAR ESTOS!)

INSERT INTO Players (
    id, first_name, last_name, email, password_hash, phone, gender, birth_date,
    location, dominant_hand, backhand_type, racquet, photo_url,
    initial_position, current_position, points,
    activity_index_single, challenges_emitted_single, challenges_accepted_single, challenges_won_single, defenses_successful_single, activity_status_single,
    activity_index_doubles, challenges_emitted_doubles, challenges_accepted_doubles, challenges_won_doubles, defenses_successful_doubles, activity_status_doubles,
    rejections_current_cycle, rejections_total, activity_status, last_activity_update, last_challenge_received_date
    -- La columna 'registration_type' ha sido eliminada de aquí
) VALUES
-- CADA FILA AHORA DEBE TENER 33 VALORES
(1, 'Carlos', 'Alcaraz', 'carlos.a@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue1', NULL, 'Masculino', '2003-05-05', 'Murcia', 'Derecha', 'Dos manos', 'Babolat', NULL, 1, 1, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(2, 'Iga', 'Swiatek', 'iga.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue2', NULL, 'Femenino', '2001-05-31', 'Varsovia', 'Derecha', 'Dos manos', 'Tecnifibre', NULL, 2, 2, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(3, 'Jannik', 'Sinner', 'jannik.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue3', NULL, 'Masculino', '2001-08-16', 'San Candido', 'Derecha', 'Dos manos', 'Head', NULL, 3, 3, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(4, 'Aryna', 'Sabalenka', 'aryna.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue4', NULL, 'Femenino', '1998-05-05', 'Minsk', 'Derecha', 'Dos manos', 'Wilson', NULL, 4, 4, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(5, 'Daniil', 'Medvedev', 'daniil.m@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue5', NULL, 'Masculino', '1996-02-11', 'Moscú', 'Derecha', 'Dos manos', 'Tecnifibre', NULL, 5, 5, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(6, 'Elena', 'Rybakina', 'elena.r@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue6', NULL, 'Femenino', '1999-06-17', 'Moscú', 'Derecha', 'Dos manos', 'Yonex', NULL, 6, 6, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(7, 'Stefanos', 'Tsitsipas', 'stefanos.t@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue7', NULL, 'Masculino', '1998-08-12', 'Atenas', 'Derecha', 'Una mano', 'Wilson', NULL, 7, 7, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(8, 'Coco', 'Gauff', 'coco.g@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue8', NULL, 'Femenino', '2004-03-13', 'Atlanta', 'Derecha', 'Dos manos', 'Head', NULL, 8, 8, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(9, 'Alexander', 'Zverev', 'alex.z@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue9', NULL, 'Masculino', '1997-04-20', 'Hamburgo', 'Derecha', 'Dos manos', 'Head', NULL, 9, 9, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(10, 'Jessica', 'Pegula', 'jessica.p@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue10', NULL, 'Femenino', '1994-02-24', 'Buffalo', 'Derecha', 'Dos manos', 'Yonex', NULL, 10, 10, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(11, 'Hubert', 'Hurkacz', 'hubert.h@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue11', NULL, 'Masculino', '1997-02-11', NULL, 'Derecha', 'Dos manos', NULL, NULL, 11, 11, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(12, 'Maria', 'Sakkari', 'maria.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue12', NULL, 'Femenino', '1995-07-25', NULL, 'Derecha', 'Dos manos', NULL, NULL, 12, 12, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(13, 'Taylor', 'Fritz', 'taylor.f@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue13', NULL, 'Masculino', '1997-10-28', NULL, 'Derecha', 'Dos manos', NULL, NULL, 13, 13, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(14, 'Ons', 'Jabeur', 'ons.j@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue14', NULL, 'Femenino', '1994-08-28', NULL, 'Derecha', 'Dos manos', NULL, NULL, 14, 14, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(15, 'Andrey', 'Rublev', 'andrey.r@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue15', NULL, 'Masculino', '1997-10-20', NULL, 'Derecha', 'Dos manos', NULL, NULL, 15, 15, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(16, 'Marketa', 'Vondrousova', 'marketa.v@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue16', NULL, 'Femenino', '1999-06-28', NULL, 'Izquierda', 'Dos manos', NULL, NULL, 16, 16, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(17, 'Casper', 'Ruud', 'casper.r@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue17', NULL, 'Masculino', '1998-12-22', NULL, 'Derecha', 'Dos manos', NULL, NULL, 17, 17, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(18, 'Beatriz', 'Haddad Maia', 'beatriz.h@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue18', NULL, 'Femenino', '1996-05-11', NULL, 'Izquierda', 'Dos manos', NULL, NULL, 18, 18, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(19, 'Alex', 'De Minaur', 'alex.d@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue19', NULL, 'Masculino', '1999-02-17', NULL, 'Derecha', 'Dos manos', NULL, NULL, 19, 19, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(20, 'Veronika', 'Kudermetova', 'veronika.k@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue20', NULL, 'Femenino', '1997-04-24', NULL, 'Derecha', 'Dos manos', NULL, NULL, 20, 20, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(21, 'Frances', 'Tiafoe', 'frances.t@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue21', NULL, 'Masculino', '1998-01-20', NULL, 'Derecha', 'Dos manos', NULL, NULL, 21, 21, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(22, 'Victoria', 'Azarenka', 'victoria.a@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue22', NULL, 'Femenino', '1989-07-31', NULL, 'Derecha', 'Dos manos', NULL, NULL, 22, 22, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(23, 'Tommy', 'Paul', 'tommy.p@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue23', NULL, 'Masculino', '1997-05-25', NULL, 'Derecha', 'Dos manos', NULL, NULL, 23, 23, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(24, 'Belinda', 'Bencic', 'belinda.b@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue24', NULL, 'Femenino', '1997-03-10', NULL, 'Derecha', 'Dos manos', NULL, NULL, 24, 24, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(25, 'Karen', 'Khachanov', 'karen.k@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue25', NULL, 'Masculino', '1996-05-21', NULL, 'Derecha', 'Dos manos', NULL, NULL, 25, 25, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(26, 'Donna', 'Vekic', 'donna.v@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue26', NULL, 'Femenino', '1996-06-28', NULL, 'Derecha', 'Dos manos', NULL, NULL, 26, 26, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(27, 'Grigor', 'Dimitrov', 'grigor.d@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue27', NULL, 'Masculino', '1991-05-16', NULL, 'Derecha', 'Una mano', NULL, NULL, 27, 27, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(28, 'Elise', 'Mertens', 'elise.m@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue28', NULL, 'Femenino', '1995-11-17', NULL, 'Derecha', 'Dos manos', NULL, NULL, 28, 28, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(29, 'Denis', 'Shapovalov', 'denis.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue29', NULL, 'Masculino', '1999-04-15', NULL, 'Izquierda', 'Una mano', NULL, NULL, 29, 29, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL),
(30, 'Leylah', 'Fernandez', 'leylah.f@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue30', NULL, 'Femenino', '2002-09-06', NULL, 'Izquierda', 'Dos manos', NULL, NULL, 30, 30, 0, 0,0,0,0,0, 'rojo', 0,0,0,0,0, 'rojo', 0,0, 'rojo', CURRENT_TIMESTAMP, NULL);


-- DATOS INICIALES DE EJEMPLO PARA TORNEOS (NUEVOS)
INSERT INTO Tournaments (
    id, name, start_date, end_date, registration_start_date, registration_end_date,
    type, status, description, rules_url, is_active, is_published,
    category, max_slots, cost, requirements, location, organizer_id
) VALUES
(1, 'Liga Pirámide Principal (Individual)', '2025-01-01', '2025-12-31', '2024-12-01 00:00:00', '2025-01-31 23:59:59',
 'pyramid_single', 'in_progress', 'Ranking continuo de individuales del club.', NULL, 1, 1,
 'Abierta', 0, 0.0, NULL, 'Club Central', 1),
(2, 'Liga Pirámide Principal (Dobles Masculino)', '2025-01-01', '2025-12-31', '2024-12-01 00:00:00', '2025-01-31 23:59:59',
 'pyramid_doubles_male', 'in_progress', 'Ranking continuo de dobles masculinos del club.', NULL, 1, 1,
 'Abierta', 0, 0.0, NULL, 'Club Central', 1),
(5, 'Liga Pirámide Principal (Dobles Femenino)', '2025-01-01', '2025-12-31', '2024-12-01 00:00:00', '2025-01-31 23:59:59',
 'pyramid_doubles_female', 'in_progress', 'Ranking continuo de dobles femeninos del club.', NULL, 0, 0,
 'Abierta', 0, 0.0, NULL, 'Club Central', 1),
(3, 'Torneo Satélite de Verano - Individual Mixto', '2025-07-01', '2025-07-31', '2025-07-01 00:00:00', '2025-07-31 23:59:59', -- Fechas ajustadas para que sean inscribibles
 'satellite_single', 'registration_open', 'Torneo individual abierto a todos los géneros, ranking independiente.', NULL, 0, 1,
 'Mixta', 20, 15.0, 'Para mayores de 18', 'Canchas del Parque', 1),
(4, 'Torneo Satélite de Verano - Dobles Mixto', '2025-07-01', '2025-07-31', '2025-07-01 00:00:00', '2025-07-31 23:59:59', -- Fechas ajustadas para que sean inscribibles
 'satellite_doubles_mixed', 'registration_open', 'Torneo de dobles mixto, ranking independiente.', NULL, 0, 1,
 'Mixta', 16, 25.0, 'Inscripción en pareja', 'Canchas del Parque', 1);

-- DATOS DE EJEMPLO PARA LA TABLA TEAMS (GLOBAL)
-- Estas son solo las parejas, sin ranking ni actividad específica por torneo aquí
INSERT INTO Teams (id, player1_id, player2_id, team_name, gender_category) VALUES
(1, 1, 3, 'Alcaraz/Sinner (Global)', 'Masculino'),   -- Carlos Alcaraz (1), Jannik Sinner (3)
(2, 5, 7, 'Medvedev/Tsitsipas (Global)', 'Masculino'), -- Daniil Medvedev (5), Stefanos Tsitsipas (7)
(3, 2, 4, 'Swiatek/Sabalenka (Global)', 'Femenino'),   -- Iga Swiatek (2), Aryna Sabalenka (4)
(4, 6, 8, 'Rybakina/Gauff (Global)', 'Femenino');     -- Elena Rybakina (6), Coco Gauff (8)


-- DATOS DE EJEMPLO PARA TournamentTeams (Ranking de Dobles para LIGA PIRAMIDE PRINCIPAL)
-- Solo para los equipos que participan en la pirámide de dobles, referenciando el Torneo 2
INSERT INTO TournamentTeams (
    tournament_id, team_id, tournament_current_position, tournament_initial_position, tournament_points,
    activity_index_team_doubles, challenges_emitted_team_doubles, challenges_accepted_team_doubles,
    challenges_won_team_doubles, defenses_successful_team_doubles, rejections_team_doubles_current_cycle,
    rejections_team_doubles_total, activity_status_team_doubles, last_activity_team_doubles_update
) VALUES
(2, 1, 1, 1, 0, 0,0,0,0,0, 0,0, 'rojo', CURRENT_TIMESTAMP), -- Alcaraz/Sinner en Torneo 2
(2, 2, 2, 2, 0, 0,0,0,0,0, 0,0, 'rojo', CURRENT_TIMESTAMP), -- Medvedev/Tsitsipas en Torneo 2
(5, 3, 3, 3, 0, 0,0,0,0,0, 0,0, 'rojo', CURRENT_TIMESTAMP); -- Swiatek/Sabalenka en Torneo 2 (ejemplo, aunque son femeninas en torneo masculino)


-- DATOS DE EJEMPLO PARA TournamentRegistrations (Registrar jugadores al Torneo Pirámide Individual)
-- Aquí registramos algunos jugadores al Torneo 1 (Liga Pirámide Principal Individual)
INSERT INTO TournamentRegistrations (tournament_id, player_id, registration_date, status) VALUES
(1, 1, STRFTIME('%Y-%m-%d %H:%M:%S', 'now', '-10 days'), 'approved'),
(1, 2, STRFTIME('%Y-%m-%d %H:%M:%S', 'now', '-9 days'), 'approved'),
(1, 3, STRFTIME('%Y-%m-%d %H:%M:%S', 'now', '-8 days'), 'approved');

-- DATOS DE EJEMPLO PARA Matches (Partidos Individuales)
-- Asociaremos los partidos al Torneo Pirámide Individual (id=1)
INSERT INTO Matches (tournament_id, date, challenger_id, challenged_id, winner_id, loser_id, score_text, is_challenger_winner, positions_swapped, status) VALUES
(1, '2025-01-10 10:00:00', 3, 5, 3, 5, '6-4, 6-2', 1, 1, 'valid'), -- Jannik Sinner (3) gana a Daniil Medvedev (5) en Torneo 1
(1, '2025-01-15 14:00:00', 1, 3, 1, 3, '7-6, 6-3', 1, 1, 'valid'); -- Carlos Alcaraz (1) gana a Jannik Sinner (3) en Torneo 1


-- DATOS DE EJEMPLO PARA Challenges (Desafíos Individuales)
-- Asociaremos los desafíos al Torneo Pirámide Individual (id=1)
INSERT INTO Challenges (tournament_id, challenger_id, challenged_id, status, created_at) VALUES
(1, 7, 6, 'pending', '2025-07-16 10:00:00'), -- Stefanos Tsitsipas (7) desafía a Elena Rybakina (6) en Torneo 1
(1, 9, 8, 'pending', '2025-07-16 11:00:00'); -- Alexander Zverev (9) desafía a Coco Gauff (8) en Torneo 1


-- DATOS DE EJEMPLO PARA DoublesMatches (Partidos de Dobles)
-- NOTA: team_a_id, team_b_id, winner_team_id, loser_team_id ahora deben referenciar IDS DE TOURNAMENTTEAMS
-- Tendrás que crear TournamentTeams primero y luego referenciar sus IDs aquí.
-- Esto es complejo si queremos tener datos consistentes inmediatamente.
-- Por ahora, no incluyo DoublesMatches de ejemplo hasta que ajustemos la creación de TournamentTeams.


-- DATOS DE EJEMPLO PARA DoublesPartnerRequests (Solicitudes de Compañero)
-- Asociaremos estas solicitudes a un torneo específico, ej. Torneo Satélite de Verano - Dobles Mixto (id=4)
INSERT INTO DoublesPartnerRequests (tournament_id, requester_player_id, requested_player_id, status, created_at) VALUES
(4, 1, 2, 'pending', STRFTIME('%Y-%m-%d %H:%M:%S', 'now', '-5 days')), -- Carlos Alcaraz (1) solicita a Iga Swiatek (2) para Torneo 4
(4, 4, 3, 'pending', STRFTIME('%Y-%m-%d %H:%M:%S', 'now', '-3 days')); -- Aryna Sabalenka (4) solicita a Jannik Sinner (3) para Torneo 4
