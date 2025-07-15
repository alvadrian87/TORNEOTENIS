// static/manage_doubles_teams.js

let allPlayers = []; // Para cargar los jugadores individuales
let currentFilter = 'all'; // Filtro actual para la tabla de dobles

document.addEventListener('DOMContentLoaded', () => {
    loadPlayersForDoublesTeams();
    loadDoublesTeams(); // Carga inicial de equipos
});

// Carga los jugadores individuales para los selectores de creación de equipo
async function loadPlayersForDoublesTeams() {
    try {
        const response = await fetch('/api/players');
        if (!response.ok) {
            throw new Error('Error al cargar datos de jugadores.');
        }
        allPlayers = await response.json();
        
        const player1Select = document.getElementById('player1-select');
        const player2Select = document.getElementById('player2-select');

        player1Select.innerHTML = '<option value="">Seleccione Jugador 1</option>';
        player2Select.innerHTML = '<option value="">Seleccione Jugador 2</option>';

        allPlayers.forEach(player => {
            const option = document.createElement('option');
            option.value = player.id;
            option.textContent = `${player.name} (${player.gender})`;
            player1Select.appendChild(option.cloneNode(true));
            player2Select.appendChild(option.cloneNode(true));
        });

    } catch (error) {
        console.error('Error en loadPlayersForDoublesTeams:', error);
        alert('No se pudieron cargar los jugadores para formar equipos.');
    }
}

// Crea un nuevo equipo de dobles
async function createDoublesTeam() {
    const player1Id = document.getElementById('player1-select').value;
    const player2Id = document.getElementById('player2-select').value;
    // ELIMINADO: const teamName = document.getElementById('team-name-input').value.trim();
    const messageDiv = document.getElementById('create-team-message');

    messageDiv.textContent = ''; // Limpiar mensajes previos

    if (!player1Id || !player2Id) { // Validar solo IDs de jugadores
        messageDiv.textContent = 'Por favor, seleccione ambos jugadores.';
        messageDiv.className = 'message error';
        return;
    }
    if (player1Id === player2Id) {
        messageDiv.textContent = 'Los jugadores de un equipo no pueden ser el mismo.';
        messageDiv.className = 'message error';
        return;
    }

    // Obtener los objetos de jugador para obtener sus apellidos
    const player1 = allPlayers.find(p => p.id == player1Id);
    const player2 = allPlayers.find(p => p.id == player2Id);

    if (!player1 || !player2) {
        messageDiv.textContent = 'Error: No se encontraron los datos completos de los jugadores seleccionados.';
        messageDiv.className = 'message error';
        return;
    }

    // Generar el nombre del equipo con los apellidos
    const teamName = `${player1.last_name}/${player2.last_name}`;

    try {
        const response = await fetch('/api/doubles_teams', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player1_id: parseInt(player1Id), player2_id: parseInt(player2Id), team_name: teamName })
        });
        const data = await response.json();

        if (!response.ok) {
            messageDiv.textContent = `Error: ${data.error || 'Ocurrió un error al crear el equipo.'}`;
            messageDiv.className = 'message error';
        } else {
            messageDiv.textContent = data.message;
            messageDiv.className = 'message success';
            // ELIMINADO: document.getElementById('team-name-input').value = ''; // Limpiar campo
            document.getElementById('player1-select').value = ''; // Limpiar select
            document.getElementById('player2-select').value = ''; // Limpiar select
            loadDoublesTeams(); // Recargar la lista de equipos
        }
    } catch (error) {
        console.error('Error al crear el equipo de dobles:', error);
        messageDiv.textContent = 'Error de conexión al crear el equipo.';
        messageDiv.className = 'message error';
    }
}

// Carga y muestra los equipos de dobles
async function loadDoublesTeams() {
    const teamsTbody = document.getElementById('doubles-teams-tbody');
    const loadingMessage = document.getElementById('doubles-teams-loading-message');
    
    teamsTbody.innerHTML = '';
    loadingMessage.textContent = 'Cargando equipos...';
    loadingMessage.style.display = 'block';

    let url = '/api/doubles_teams';
    if (currentFilter !== 'all') {
        url += `?gender=${currentFilter}`;
    }
    console.log(`DEBUG: loadDoublesTeams - URL de fetch: ${url}`); // NUEVO CONSOLE.LOG

    try {
        const response = await fetch(url);
        console.log(`DEBUG: loadDoublesTeams - Respuesta Status: ${response.status}`); // NUEVO CONSOLE.LOG
        if (!response.ok) {
            throw new Error('Error al cargar equipos de dobles.');
        }
        const teams = await response.json();
        console.log("DEBUG: Equipos de dobles obtenidos:", teams); // NUEVO CONSOLE.LOG

        loadingMessage.style.display = 'none';

        if (teams.length === 0) {
            loadingMessage.textContent = 'No hay equipos registrados en esta categoría.';
            loadingMessage.style.display = 'block';
            return;
        }

        teams.forEach(team => {
            const row = teamsTbody.insertRow();
            row.insertCell().textContent = team.current_position;
            row.insertCell().textContent = team.team_name;
            row.insertCell().textContent = team.player1_name;
            row.insertCell().textContent = team.player2_name;
            row.insertCell().textContent = team.gender_category;
            row.insertCell().textContent = team.initial_position;
            row.insertCell().textContent = team.points;
            // Opcional: añadir celda de acciones para editar/eliminar equipo
        });

    } catch (error) {
        console.error('Error en loadDoublesTeams:', error);
        loadingMessage.textContent = `Error al cargar equipos: ${error.message}`;
        loadingMessage.className = 'message error';
        loadingMessage.style.display = 'block';
    }
}

// Filtra los equipos por género
function filterTeams(gender) {
    console.log(`DEBUG: filterTeams - Filtro seleccionado: ${gender}`); // NUEVO CONSOLE.LOG
    currentFilter = gender;
    // Actualizar botones activos
    document.querySelectorAll('.filter-buttons button').forEach(button => {
        button.classList.remove('active');
    });
    // Asegúrate de que el ID del botón coincida con el valor del género
    document.getElementById(`filter-${gender}-teams`).classList.add('active');
    loadDoublesTeams(); // Recargar equipos con el nuevo filtro
}
