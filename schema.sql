-- schema.sql - Versión final con la tabla Challenges

-- Elimina las tablas si ya existen para un reinicio limpio
DROP TABLE IF EXISTS Matches;
DROP TABLE IF EXISTS Challenges; -- Añadido para asegurar reinicio limpio
DROP TABLE IF EXISTS Players;

-- Tabla de Jugadores
CREATE TABLE IF NOT EXISTS Players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone TEXT,
    gender TEXT,
    birth_date TEXT,
    location TEXT,
    dominant_hand TEXT,
    backhand_type TEXT,
    racquet TEXT,
    photo_url TEXT,
    category TEXT NOT NULL, -- <--- ¡AÑADE ESTA LÍNEA!
    initial_position INTEGER NOT NULL,
    current_position INTEGER NOT NULL,
    points INTEGER DEFAULT 0
);

-- Tabla de Partidos
CREATE TABLE Matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    challenger_id INTEGER NOT NULL,
    challenged_id INTEGER NOT NULL,
    winner_id INTEGER NOT NULL,
    loser_id INTEGER NOT NULL,
    score_text TEXT NOT NULL,
    is_challenger_winner BOOLEAN NOT NULL,
    positions_swapped BOOLEAN NOT NULL,
    status TEXT NOT NULL DEFAULT 'valid',
    FOREIGN KEY (challenger_id) REFERENCES Players (id),
    FOREIGN KEY (challenged_id) REFERENCES Players (id),
    FOREIGN KEY (winner_id) REFERENCES Players (id),
    FOREIGN KEY (loser_id) REFERENCES Players (id)
);

-- Tabla de Desafíos Pendientes (¡LA TABLA QUE FALTABA!)
-- En schema.sql
CREATE TABLE IF NOT EXISTS Challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenger_id INTEGER NOT NULL,
    challenged_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'played', 'cancelled'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    scheduled_date TEXT, -- Opcional: si quieres fechas programadas
    FOREIGN KEY (challenger_id) REFERENCES Players(id),
    FOREIGN KEY (challenged_id) REFERENCES Players(id)
);

-- En schema.sql, añade estas tablas al final

-- Tabla para Equipos de Dobles
CREATE TABLE IF NOT EXISTS Teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_id INTEGER NOT NULL,
    player2_id INTEGER NOT NULL,
    team_name TEXT UNIQUE NOT NULL,
    gender_category TEXT NOT NULL, -- <--- ¡NUEVA COLUMNA AQUÍ! (ej. 'Masculino', 'Femenino')
    current_position INTEGER NOT NULL,
    initial_position INTEGER NOT NULL,
    points INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player1_id) REFERENCES Players(id),
    FOREIGN KEY (player2_id) REFERENCES Players(id),
    UNIQUE (player1_id, player2_id)
);

-- Tabla para Partidos de Dobles
CREATE TABLE IF NOT EXISTS DoublesMatches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATETIME DEFAULT CURRENT_TIMESTAMP,
        team_a_id INTEGER NOT NULL,
        team_b_id INTEGER NOT NULL,
        winner_team_id INTEGER,
        loser_team_id INTEGER,
        score_text TEXT,
        is_team_a_winner INTEGER,
        positions_swapped INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- <--- ¡AÑADE ESTA LÍNEA!
        FOREIGN KEY (team_a_id) REFERENCES Teams(id),
        FOREIGN KEY (team_b_id) REFERENCES Teams(id),
        FOREIGN KEY (winner_team_id) REFERENCES Teams(id),
        FOREIGN KEY (loser_team_id) REFERENCES Teams(id)
    );


-- En schema.sql
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0 -- 1 para admin, 0 para usuario normal (opcional, para roles futuros)
);


-- Datos iniciales de ejemplo
-- Asegúrate de que esta sentencia INSERT esté en tu schema.sql
-- Y que la tabla Players esté definida con todas estas columnas:
-- id, first_name, last_name, email, password_hash, phone, gender, birth_date, location,
-- dominant_hand, backhand_type, racquet, photo_url, category, initial_position, current_position, points

INSERT INTO Players (
    id, first_name, last_name, email, password_hash, phone, gender, birth_date,
    location, dominant_hand, backhand_type, racquet, photo_url, category,
    initial_position, current_position, points
) VALUES
(1, 'Carlos', 'Alcaraz', 'carlos.a@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue1', NULL, 'Masculino', '2003-05-05', 'Murcia', 'Derecha', 'Dos manos', 'Babolat', NULL, 'Profesional', 1, 1, 0),
(2, 'Iga', 'Swiatek', 'iga.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue2', NULL, 'Femenino', '2001-05-31', 'Varsovia', 'Derecha', 'Dos manos', 'Tecnifibre', NULL, 'Profesional', 2, 2, 0),
(3, 'Jannik', 'Sinner', 'jannik.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue3', NULL, 'Masculino', '2001-08-16', 'San Candido', 'Derecha', 'Dos manos', 'Head', NULL, 'Profesional', 3, 3, 0),
(4, 'Aryna', 'Sabalenka', 'aryna.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue4', NULL, 'Femenino', '1998-05-05', 'Minsk', 'Derecha', 'Dos manos', 'Wilson', NULL, 'Profesional', 4, 4, 0),
(5, 'Daniil', 'Medvedev', 'daniil.m@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue5', NULL, 'Masculino', '1996-02-11', 'Moscú', 'Derecha', 'Dos manos', 'Tecnifibre', NULL, 'Profesional', 5, 5, 0),
(6, 'Elena', 'Rybakina', 'elena.r@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue6', NULL, 'Femenino', '1999-06-17', 'Moscú', 'Derecha', 'Dos manos', 'Yonex', NULL, 'Profesional', 6, 6, 0),
(7, 'Stefanos', 'Tsitsipas', 'stefanos.t@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue7', NULL, 'Masculino', '1998-08-12', 'Atenas', 'Derecha', 'Una mano', 'Wilson', NULL, 'Profesional', 7, 7, 0),
(8, 'Coco', 'Gauff', 'coco.g@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue8', NULL, 'Femenino', '2004-03-13', 'Atlanta', 'Derecha', 'Dos manos', 'Head', NULL, 'Profesional', 8, 8, 0),
(9, 'Alexander', 'Zverev', 'alex.z@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue9', NULL, 'Masculino', '1997-04-20', 'Hamburgo', 'Derecha', 'Dos manos', 'Head', NULL, 'Profesional', 9, 9, 0),
(10, 'Jessica', 'Pegula', 'jessica.p@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue10', NULL, 'Femenino', '1994-02-24', 'Buffalo', 'Derecha', 'Dos manos', 'Yonex', NULL, 'Profesional', 10, 10, 0),
(11, 'Hubert', 'Hurkacz', 'hubert.h@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue11', NULL, 'Masculino', '1997-02-11', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 11, 11, 0),
(12, 'Maria', 'Sakkari', 'maria.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue12', NULL, 'Femenino', '1995-07-25', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 12, 12, 0),
(13, 'Taylor', 'Fritz', 'taylor.f@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue13', NULL, 'Masculino', '1997-10-28', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 13, 13, 0),
(14, 'Ons', 'Jabeur', 'ons.j@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue14', NULL, 'Femenino', '1994-08-28', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 14, 14, 0),
(15, 'Andrey', 'Rublev', 'andrey.r@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue15', NULL, 'Masculino', '1997-10-20', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 15, 15, 0),
(16, 'Marketa', 'Vondrousova', 'marketa.v@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue16', NULL, 'Femenino', '1999-06-28', NULL, 'Izquierda', 'Dos manos', NULL, NULL, 'Profesional', 16, 16, 0),
(17, 'Casper', 'Ruud', 'casper.r@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue17', NULL, 'Masculino', '1998-12-22', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 17, 17, 0),
(18, 'Beatriz', 'Haddad Maia', 'beatriz.h@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue18', NULL, 'Femenino', '1996-05-11', NULL, 'Izquierda', 'Dos manos', NULL, NULL, 'Profesional', 18, 18, 0),
(19, 'Alex', 'De Minaur', 'alex.d@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue19', NULL, 'Masculino', '1999-02-17', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 19, 19, 0),
(20, 'Veronika', 'Kudermetova', 'veronika.k@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue20', NULL, 'Femenino', '1997-04-24', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 20, 20, 0),
(21, 'Frances', 'Tiafoe', 'frances.t@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue21', NULL, 'Masculino', '1998-01-20', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 21, 21, 0),
(22, 'Victoria', 'Azarenka', 'victoria.a@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue22', NULL, 'Femenino', '1989-07-31', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 22, 22, 0),
(23, 'Tommy', 'Paul', 'tommy.p@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue23', NULL, 'Masculino', '1997-05-25', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 23, 23, 0),
(24, 'Belinda', 'Bencic', 'belinda.b@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue24', NULL, 'Femenino', '1997-03-10', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 24, 24, 0),
(25, 'Karen', 'Khachanov', 'karen.k@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue25', NULL, 'Masculino', '1996-05-21', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 25, 25, 0),
(26, 'Donna', 'Vekic', 'donna.v@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue26', NULL, 'Femenino', '1996-06-28', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 26, 26, 0),
(27, 'Grigor', 'Dimitrov', 'grigor.d@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue27', NULL, 'Masculino', '1991-05-16', NULL, 'Derecha', 'Una mano', NULL, NULL, 'Profesional', 27, 27, 0),
(28, 'Elise', 'Mertens', 'elise.m@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue28', NULL, 'Femenino', '1995-11-17', NULL, 'Derecha', 'Dos manos', NULL, NULL, 'Profesional', 28, 28, 0),
(29, 'Denis', 'Shapovalov', 'denis.s@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue29', NULL, 'Masculino', '1999-04-15', NULL, 'Izquierda', 'Una mano', NULL, NULL, 'Profesional', 29, 29, 0),
(30, 'Leylah', 'Fernandez', 'leylah.f@example.com', 'pbkdf2:sha256:260000$dummyhash$dummyhashvalue30', NULL, 'Femenino', '2002-09-06', NULL, 'Izquierda', 'Dos manos', NULL, NULL, 'Profesional', 30, 30, 0);