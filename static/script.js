    // static/script.js

    let currentRankingType = 'single'; 

    document.addEventListener('DOMContentLoaded', loadTournamentData);

    async function loadTournamentData() {
        filterRankings('single'); 
    }

    async function loadRankings() {
        const singleContainer = document.getElementById('single-ranking-container');
        const doublesMasculinoContainer = document.getElementById('doubles-masculino-ranking-container');
        const doublesFemeninoContainer = document.getElementById('doubles-femenino-ranking-container');

        singleContainer.style.display = 'none';
        doublesMasculinoContainer.style.display = 'none';
        doublesFemeninoContainer.style.display = 'none';

        let url = '';
        let targetTbody = null;
        let headers = [];

        if (currentRankingType === 'single') {
            url = '/api/players';
            targetTbody = document.querySelector('#leaderboard tbody');
            headers = ['Foto', 'Puesto', 'Jugador', 'Género', 'Puesto Inicial', 'Puestos Subidos', 'Acciones'];
            singleContainer.style.display = 'block'; 
        } else if (currentRankingType === 'doubles_masculino') {
            url = '/api/doubles_teams?gender=Masculino';
            targetTbody = document.querySelector('#doubles-masculino-leaderboard tbody');
            headers = ['Puesto', 'Equipo', 'Jugador 1', 'Jugador 2', 'Puesto Inicial', 'Puntos'];
            doublesMasculinoContainer.style.display = 'block'; 
        } else if (currentRankingType === 'doubles_femenino') {
            url = '/api/doubles_teams?gender=Femenino';
            targetTbody = document.querySelector('#doubles-femenino-leaderboard tbody');
            headers = ['Puesto', 'Equipo', 'Jugador 1', 'Jugador 2', 'Puesto Inicial', 'Puntos'];
            doublesFemeninoContainer.style.display = 'block'; 
        } else {
            console.error("Tipo de ranking desconocido:", currentRankingType);
            return;
        }

        if (!targetTbody) {
            console.error(`ERROR: tbody no encontrado para el tipo de ranking: ${currentRankingType}`);
            return;
        }

        targetTbody.innerHTML = '<tr><td colspan="'+ headers.length +'">Cargando...</td></tr>'; 

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log(`Datos obtenidos para ${currentRankingType}:`, data);

            renderRankingTable(data, targetTbody, headers, currentRankingType);

        } catch (error) {
            console.error(`Error al cargar el ranking (${currentRankingType}):`, error);
            targetTbody.innerHTML = `<tr><td colspan="`+ headers.length +`" style="color: red;">Error al cargar el ranking: ${error.message}</td></tr>`;
            alert(`No se pudieron cargar los datos del ranking ${currentRankingType}.`);
        }
    }

    function renderRankingTable(data, tbodyElement, headers, type) {
        tbodyElement.innerHTML = ''; 

        const theadRow = tbodyElement.previousElementSibling.querySelector('tr');
        theadRow.innerHTML = ''; 
        headers.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            theadRow.appendChild(th);
        });

        if (data.length === 0) {
            tbodyElement.innerHTML = '<tr><td colspan="'+ headers.length +'">No hay jugadores/equipos registrados en este ranking.</td></tr>';
            return;
        }

        data.forEach(item => {
            const row = tbodyElement.insertRow();

            if (type === 'single') {
                const photoCell = row.insertCell();
                const img = document.createElement('img');
                img.className = 'player-photo';
                img.src = item.photo_url ? `/static/uploads/${item.photo_url}` : 'https://i.imgur.com/sC53v2i.png';
                photoCell.appendChild(img);

                row.insertCell().textContent = item.current_position;
                const playerCell = row.insertCell();
                const playerLink = document.createElement('a');
                playerLink.href = `/player/${item.id}`;
                playerLink.textContent = item.name;
                playerCell.appendChild(playerLink);

                const genderCell = row.insertCell();
                const genderIcon = document.createElement('i');
                if (item.gender === 'Masculino') {
                    genderIcon.className = 'fas fa-mars gender-icon male';
                } else if (item.gender === 'Femenino') {
                    genderIcon.className = 'fas fa-venus gender-icon female';
                }
                genderCell.appendChild(genderIcon);

                row.insertCell().textContent = item.initial_position;
                const positionsClimbed = item.initial_position - item.current_position;
                const climbCell = row.insertCell();
                climbCell.textContent = positionsClimbed > 0 ? `+${positionsClimbed}` : positionsClimbed;

                const actionsCell = row.insertCell();
                const historyButton = document.createElement('button');
                historyButton.textContent = 'Ver Historial';
                historyButton.onclick = () => showPlayerHistory(item.id, item.name);
                actionsCell.appendChild(historyButton);

            } else if (type.startsWith('doubles_')) {
                row.insertCell().textContent = item.current_position;
                row.insertCell().textContent = item.team_name;
                row.insertCell().textContent = item.player1_name;
                row.insertCell().textContent = item.player2_name;
                row.insertCell().textContent = item.initial_position;
                row.insertCell().textContent = item.points;
            }
        });
    }

    function filterRankings(type) {
        currentRankingType = type;

        document.querySelectorAll('.ranking-filters button').forEach(button => {
            button.classList.remove('active');
        });
        
        const activeButton = document.getElementById(`filter-${type}`); // <--- LÍNEA DEL ERROR
        console.log(`DEBUG: filterRankings - Buscando botón con ID: filter-${type}`); // NUEVO CONSOLE.LOG
        if (activeButton) { // Añadir una verificación de null
            activeButton.classList.add('active');
        } else {
            console.error(`ERROR: Botón con ID filter-${type} no encontrado.`);
        }
        
        loadRankings(); 
    }

    async function showPlayerHistory(playerId, playerName) {
        document.getElementById('player-history-name').textContent = playerName;
        document.getElementById('leaderboard-section').style.display = 'none';
        document.getElementById('player-history-section').style.display = 'block';

        const historyList = document.getElementById('player-history-list');
        historyList.innerHTML = '<p>Cargando historial...</p>';

        try {
            const response = await fetch(`/api/players/${playerId}/history`);
            if (!response.ok) {
                throw new Error('No se pudo cargar el historial.');
            }
            const matches = await response.json();

            historyList.innerHTML = ''; 
            if (matches.length === 0) {
                historyList.innerHTML = '<p>Este jugador aún no ha jugado partidos.</p>';
                return;
            }

            matches.forEach(match => {
                const matchDiv = document.createElement('div');
                matchDiv.className = 'match-item'; 
                
                let resultText = '';
                if (match.match_type === 'single') {
                    resultText = `${match.challenger_name} vs ${match.challenged_name}`;
                } else if (match.match_type === 'doubles') {
                    resultText = `${match.challenger_name} vs ${match.challenged_name} (Dobles)`;
                } else {
                    resultText = 'Tipo de partido desconocido';
                }

                matchDiv.innerHTML = `
                    <p><strong>Fecha:</strong> ${new Date(match.date).toLocaleDateString()}</p>
                    <p><strong>Resultado:</strong> ${resultText}</p>
                    <p><strong>Ganador:</strong> ${match.winner_name} (<strong>${match.score_text}</strong>)</p>
                    <hr>
                `;
                historyList.appendChild(matchDiv);
            });

        } catch (error) {
            console.error('Error al cargar el historial del jugador:', error);
            historyList.innerHTML = '<p style="color: red;">Error al cargar el historial.</p>';
        }
    }

    function hidePlayerHistory() {
        document.getElementById('player-history-section').style.display = 'none';
        document.getElementById('leaderboard-section').style.display = 'block';
    }

    function challengePlayer(challengedId, challengedName) {
        alert("La función de desafiar directamente desde la tabla ha sido deshabilitada.");
        window.location.href = '/organizer';
    }

    function closeChallengeModal() {
        const modal = document.getElementById('challenge-modal');
        modal.style.display = 'none';
    }

    async function confirmChallenge() {
        // Esta función ya no se llamaría desde index.html si el modal fue eliminado
    }
    