// static/organizer/organizer.js

let allPlayers = [];
let allDoublesTeams = []; // Variable global para almacenar los equipos de dobles

document.addEventListener('DOMContentLoaded', () => {
    loadPlayersForOrganizer();
    loadPendingChallengesForOrganizer(); // Carga desafíos individuales pendientes
    loadDoublesTeamsForOrganizer(); // Carga los equipos de dobles al inicio
    loadPendingDoublesChallengesForOrganizer(); // Carga los desafíos de dobles pendientes al inicio
});

// FUNCIÓN: Carga los jugadores individuales para los selectores
async function loadPlayersForOrganizer() {
    try {
        const response = await fetch('/api/players');
        if (!response.ok) {
            throw new Error('Error al cargar datos de jugadores.');
        }
        allPlayers = await response.json();
        
        const challengerSelect = document.getElementById('challenger-select');
        const challengedSelect = document.getElementById('challenged-select');
        const historySelect = document.getElementById('history-player-select');

        challengerSelect.innerHTML = '<option value="">Seleccione un desafiante</option>';
        challengedSelect.innerHTML = '<option value="">Seleccione un desafiado</option>';
        if (historySelect) historySelect.innerHTML = '<option value="">Seleccione un jugador</option>';

        allPlayers.forEach(player => {
            const option = document.createElement('option');
            option.value = player.id;
            option.textContent = `${player.name} (Puesto: ${player.current_position})`;
            challengerSelect.appendChild(option.cloneNode(true));
            challengedSelect.appendChild(option.cloneNode(true));
            if (historySelect) historySelect.appendChild(option.cloneNode(true));
        });

    } catch (error) {
        console.error('Error en loadPlayersForOrganizer:', error);
        alert('No se pudieron cargar los jugadores para el organizador.');
    }
}

// FUNCIÓN: Valida un desafío individual
async function validateChallenge() {
    console.log("--- FUNCIÓN: validateChallenge() INICIADA ---");
    const challengerSelect = document.getElementById('challenger-select');
    const challengedSelect = document.getElementById('challenged-select');

    const challengerId = challengerSelect.value;
    const challengedId = challengedSelect.value;
    console.log(`IDs seleccionados: Desafiante=${challengerId}, Desafiado=${challengedId}`);

    const validationMessage = document.getElementById('challenge-validation-message');
    const scoreForm = document.getElementById('score-entry-form');

    validationMessage.textContent = '';
    scoreForm.style.display = 'none';

    if (!challengerId || !challengedId || parseInt(challengerId) === parseInt(challengedId)) {
        validationMessage.textContent = 'Por favor, seleccione dos jugadores diferentes.';
        validationMessage.className = 'message error';
        console.warn("Validación frontend fallida: IDs inválidos o iguales.");
        return;
    }

    try {
        console.log("Intentando llamar a /api/validate_challenge (backend para validación).");
        const response = await fetch('/api/validate_challenge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ challengerId: parseInt(challengerId), challengedId: parseInt(challengedId) })
        });
        console.log(`Respuesta de /api/validate_challenge - Status: ${response.status}`);
        const data = await response.json();
        console.log("Datos recibidos de /api/validate_challenge:", data);

        validationMessage.textContent = data.message;
        if (data.valid) {
            validationMessage.className = 'message success';
            scoreForm.style.display = 'block';
            console.log("Validación backend exitosa. Llamando a proposeChallenge()...");
            await proposeChallenge(parseInt(challengerId), parseInt(challengedId));
        } else {
            validationMessage.className = 'message error';
            console.log("Validación backend fallida: Desafío no permitido.");
        }
    } catch (error) {
        console.error('ERROR en validateChallenge (fetch o JSON):', error);
        validationMessage.textContent = 'Error de conexión al validar el desafío.';
        validationMessage.className = 'message error';
    }
}

// FUNCIÓN: Propone un desafío individual
async function proposeChallenge(challengerId, challengedId) {
    console.log(`--- FUNCIÓN: proposeChallenge() INICIADA con Desafiante=${challengerId}, Desafiado=${challengedId} ---`);
    try {
        const response = await fetch('/api/propose_challenge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ challengerId, challengedId })
        });
        const data = await response.json();

        if (!response.ok) {
            if (response.status === 409) {
                 alert(`Atención: ${data.error}`);
            } else {
                 throw new Error(data.error || 'Error desconocido al proponer el desafío.');
            }
        } else {
            alert(data.message);
            console.log("Desafío propuesto exitosamente. Recargando desafíos pendientes.");
            loadPendingChallengesForOrganizer();
        }
    } catch (error) {
        console.error('ERROR al proponer el desafío:', error);
        alert(`Error al proponer el desafío: ${error.message}`);
    }
}

// FUNCIÓN: Carga y muestra los desafíos individuales pendientes
async function loadPendingChallengesForOrganizer() {
    console.log("--- FUNCIÓN: loadPendingChallengesForOrganizer() INICIADA ---");
    const pendingChallengesListDiv = document.getElementById('pending-challenges-list'); 
    if (!pendingChallengesListDiv) {
        console.warn("Elemento 'pending-challenges-list' no encontrado en el DOM de organizer.html.");
        return;
    }

    pendingChallengesListDiv.innerHTML = '<p>Cargando desafíos pendientes...</p>';

    try {
        const response = await fetch('/api/pending_challenges'); 
        console.log(`Respuesta de /api/pending_challenges - Status: ${response.status}`);
        if (!response.ok) {
            throw new Error('Error al cargar los desafíos pendientes.');
        }
        const challenges = await response.json();
        console.log("Desafíos pendientes obtenidos (organizer):", challenges);

        pendingChallengesListDiv.innerHTML = '';

        if (challenges.length === 0) {
            pendingChallengesListDiv.innerHTML = '<p>No hay desafíos pendientes en este momento.</p>';
            return;
        }

        const ul = document.createElement('ul');
        ul.style.listStyle = 'none';
        ul.style.padding = '0';

        challenges.forEach(challenge => {
            const li = document.createElement('li');
            li.style.marginBottom = '10px';
            li.style.padding = '8px';
            li.style.border = '1px solid #ddd';
            li.style.borderRadius = '4px';
            li.style.backgroundColor = '#f9f9f9';

            li.innerHTML = `
                <span>
                    Desafío #${challenge.id}: <strong>${challenge.challenger_name}</strong> vs <strong>${challenge.challenged_name}</strong> 
                    (creado: ${new Date(challenge.created_at).toLocaleDateString()})
                </span>
                <button onclick="startMatchResultEntry(${challenge.id}, ${challenge.challenger_id}, ${challenge.challenged_id})" class="button" style="margin-left: 10px; background-color: #28a745; font-size: 0.8em; padding: 4px 8px;">
                    Ingresar Resultado
                </button>
                <button onclick="cancelPendingChallenge(${challenge.id})" class="button" style="margin-left: 5px; background-color: #ffc107; font-size: 0.8em; padding: 4px 8px;">
                    Cancelar
                </button>
            `;
            ul.appendChild(li);
        });
        pendingChallengesListDiv.appendChild(ul);

    } catch (error) {
        console.error('ERROR en loadPendingChallengesForOrganizer:', error);
        pendingChallengesListDiv.innerHTML = `<p style="color: red;">Error al cargar desafíos pendientes: ${error.message}</p>`;
    }
}

// FUNCIÓN: Prepara el formulario de resultado individual
function startMatchResultEntry(challengeId, challengerId, challengedId) {
    console.log(`--- FUNCIÓN: startMatchResultEntry() INICIADA con Challenge ID=${challengeId}, Desafiante=${challengerId}, Desafiado=${challengedId} ---`);
    document.getElementById('challenger-select').value = challengerId;
    document.getElementById('challenged-select').value = challengedId;
    document.getElementById('score-entry-form').style.display = 'block';
    
    const hiddenChallengeIdInput = document.getElementById('hidden-challenge-id');
    if (hiddenChallengeIdInput) {
        hiddenChallengeIdInput.value = challengeId;
        console.log(`hidden-challenge-id establecido a: ${hiddenChallengeIdInput.value}`);
    } else {
        console.warn("Input oculto para challenge ID no encontrado. El resultado del partido no actualizará el estado del desafío.");
    }

    document.getElementById('set1-challenger').value = '';
    document.getElementById('set1-challenged').value = '';
    document.getElementById('set2-challenger').value = '';
    document.getElementById('set2-challenged').value = '';
    document.getElementById('set3-challenger').value = '';
    document.getElementById('set3-challenged').value = '';
    document.getElementById('result-message').textContent = '';


    document.getElementById('score-entry-form').scrollIntoView({ behavior: 'smooth' });

    alert('Jugadores seleccionados para ingresar resultado. Por favor, complete el marcador.');
}

// FUNCIÓN: Envía el resultado del partido individual
async function submitMatchResult() {
    console.log("--- FUNCIÓN: submitMatchResult() INICIADA ---");
    const challengerId = document.getElementById('challenger-select').value;
    const challengedId = document.getElementById('challenged-select').value;
    const resultMessageDiv = document.getElementById('result-message');
    
    const hiddenChallengeIdInput = document.getElementById('hidden-challenge-id');
    const hiddenChallengeId = hiddenChallengeIdInput ? hiddenChallengeIdInput.value : null;
    console.log(`Desafiante: ${challengerId}, Desafiado: ${challengedId}, Challenge ID (oculto): ${hiddenChallengeId}`);

    const sets = [];
    for (let i = 1; i <= 3; i++) {
        const scoreChallenger = document.getElementById(`set${i}-challenger`).value;
        const scoreChallenged = document.getElementById(`set${i}-challenged`).value;
        if (scoreChallenger !== '' && scoreChallenged !== '') { // Corregido: scoreChallenger doble
            sets.push([parseInt(scoreChallenger, 10), parseInt(scoreChallenged, 10)]);
        }
    }

    if (sets.length < 2) {
        resultMessageDiv.textContent = 'Debe ingresar el resultado de al menos dos sets.';
        resultMessageDiv.className = 'message error';
        console.warn("Validación de sets fallida: Menos de 2 sets.");
        return;
    }

    try {
        console.log("Intentando llamar a /api/match_result (backend para enviar resultado).");
        const response = await fetch('/api/match_result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                challengerId: parseInt(challengerId),
                challengedId: parseInt(challengedId),
                sets: sets,
                challengeId: hiddenChallengeId ? parseInt(hiddenChallengeId) : null 
            })
        });
        const data = await response.json();
        console.log("Datos recibidos de /api/match_result:", data);

        if (response.ok) {
            alert(data.message);
            window.location.href = '/organizer'; // Recargar la página del organizador
        } else {
            resultMessageDiv.textContent = `Error: ${data.error || 'Ocurrió un error.'}`;
            resultMessageDiv.className = 'message error';
        }
    } catch (error) {
        console.error('ERROR al enviar el resultado (fetch o JSON):', error);
        resultMessageDiv.textContent = 'Error de conexión al enviar el resultado.';
        resultMessageDiv.className = 'message error';
    }
}

// FUNCIÓN: Muestra el historial de un jugador en el panel del organizador
async function showOrganizerPlayerHistory() {
    console.log("--- FUNCIÓN: showOrganizerPlayerHistory() INICIADA ---");
    const playerId = document.getElementById('history-player-select').value;
    const historyList = document.getElementById('organizer-history-list');

    if (!playerId) {
        historyList.innerHTML = '';
        console.warn("No se seleccionó ningún jugador para el historial.");
        return;
    }
    historyList.innerHTML = '<p>Cargando historial...</p>';

    try {
        console.log(`Intentando llamar a /api/players/${playerId}/history.`);
        const response = await fetch(`/api/players/${playerId}/history`);
        console.log(`Respuesta de /api/players/${playerId}/history - Status: ${response.status}`);
        if (!response.ok) throw new Error('No se pudo cargar el historial.');
        const matches = await response.json();
        console.log("Historial de partidos obtenido:", matches);
        historyList.innerHTML = '';
        
        if (matches.length === 0) {
            historyList.innerHTML = '<p>Este jugador aún no ha jugado partidos.</p>';
            return;
        }
        
        const ul = document.createElement('ul');
        ul.style.listStyle = 'none';
        ul.style.padding = '0';
        
        matches.forEach((match, index) => {
            const li = document.createElement('li');
            li.style.marginBottom = '10px';
            
            // Determinar si es partido individual o de dobles para mostrar el resultado
            let resultText = '';
            if (match.match_type === 'single') {
                resultText = `${match.challenger_name} vs ${match.challenged_name}`;
            } else if (match.match_type === 'doubles') {
                resultText = `${match.challenger_name} vs ${match.challenged_name} (Dobles)`;
            } else {
                resultText = 'Tipo de partido desconocido';
            }

            // El botón de eliminar y editar solo aparece en el partido más reciente (el primero de la lista)
            const deleteButton = (index === 0) 
                ? `<button onclick="deleteMatch(${match.id})" class="button" style="margin-left: 15px; font-size: 0.8em; padding: 4px 8px; background-color: #dc3545;">Eliminar</button>`
                : '';
            const editButton = (index === 0 && match.match_type === 'single') // Solo editar individuales por ahora
                ? `<button onclick="openEditMatchModal(${match.id})" class="button" style="margin-left: 5px; font-size: 0.8em; padding: 4px 8px; background-color: #007bff;">Editar</button>`
                : '';

            li.innerHTML = `
                <span>
                    ${new Date(match.date).toLocaleDateString()}: 
                    <strong>${match.winner_name}</strong> ganó a ${match.loser_name} (<strong>${match.score_text}</strong>)
                    <br>
                    <small>Tipo: ${match.match_type === 'single' ? 'Individual' : 'Dobles'}</small>
                </span>
                ${editButton} 
                ${deleteButton}
            `;
            ul.appendChild(li);
        });
        historyList.appendChild(ul);
    } catch (error) {
        console.error('ERROR al cargar el historial:', error);
        historyList.innerHTML = `<p style="color: red;">Error al cargar el historial: ${error.message}</p>`;
    }
}

// FUNCIÓN: Elimina un partido
async function deleteMatch(matchId) {
    if (!confirm(`¡ATENCIÓN! ¿Estás seguro de que quieres eliminar el partido con ID ${matchId}? Esta acción revierte las estadísticas y posiciones. No se puede deshacer.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/matches/${matchId}/delete`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Error desconocido');
        alert(data.message);
        showOrganizerPlayerHistory(); 
        loadPlayersForOrganizer(); 
    } catch (error) {
        alert(`Error al eliminar el partido: ${error.message}`);
    }
}

// FUNCIÓN: Reinicia la tabla de posiciones
async function resetLeaderboard() {
    const resetMessage = document.getElementById('reset-message');
    if (!confirm('¿Estás seguro de que quieres reiniciar la temporada? Esto actualizará el "Puesto Inicial" de todos a su puesto actual y reiniciará los puntos.')) {
        return;
    }
    try {
        const response = await fetch('/api/reset_leaderboard', { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            resetMessage.textContent = data.message;
            resetMessage.className = 'message success';
            loadPlayersForOrganizer();
        } else {
            resetMessage.textContent = `Error: ${data.error}`;
            resetMessage.className = 'message error';
        }
    } catch (error) {
        resetMessage.textContent = 'Error de conexión al reiniciar la tabla.';
        resetMessage.className = 'message error';
    }
}

// FUNCIÓN: Abre el modal de edición de partido
async function openEditMatchModal(matchId) {
    const modal = document.getElementById('edit-match-modal');
    const challengerNameSpan = document.getElementById('edit-challenger-name');
    const challengedNameSpan = document.getElementById('edit-challenged-name');
    const editMatchIdInput = document.getElementById('edit-match-id');
    const editResultMessageDiv = document.getElementById('edit-result-message');

    editResultMessageDiv.textContent = ''; // Limpiar mensajes previos

    try {
        // Obtener detalles del partido desde el backend
        const response = await fetch(`/api/matches/${matchId}`);
        if (!response.ok) {
            throw new Error('No se pudieron cargar los detalles del partido para editar.');
        }
        const match = await response.json();
        console.log("Detalles del partido para editar:", match);

        // Rellenar el modal con los datos del partido
        editMatchIdInput.value = match.id;
        challengerNameSpan.textContent = match.challenger_name;
        challengedNameSpan.textContent = match.challenged_name;

        // Limpiar campos de sets
        for (let i = 1; i <= 3; i++) {
            document.getElementById(`edit-set${i}-challenger`).value = '';
            document.getElementById(`edit-set${i}-challenged`).value = '';
        }

        // Rellenar sets existentes
        match.sets.forEach((set, index) => {
            if (index < 3) {
                document.getElementById(`edit-set${index + 1}-challenger`).value = set[0];
                document.getElementById(`edit-set${index + 1}-challenged`).value = set[1];
            }
        });

        modal.style.display = 'flex'; // Mostrar el modal
    } catch (error) {
        console.error('Error al abrir el modal de edición:', error);
        alert(`Error al cargar el partido para editar: ${error.message}`);
    }
}

// FUNCIÓN: Cierra el modal de edición de partido
function closeEditMatchModal() {
    const modal = document.getElementById('edit-match-modal');
    modal.style.display = 'none';
    document.getElementById('edit-result-message').textContent = ''; // Limpiar mensaje
}

// FUNCIÓN: Envía los resultados editados al backend
async function submitEditedMatchResult() {
    console.log("--- FUNCIÓN: submitEditedMatchResult() INICIADA ---");
    const matchId = document.getElementById('edit-match-id').value;
    const editResultMessageDiv = document.getElementById('edit-result-message');
    editResultMessageDiv.textContent = ''; // Limpiar mensajes previos

    const sets = [];
    for (let i = 1; i <= 3; i++) {
        const scoreChallenger = document.getElementById(`edit-set${i}-challenger`).value;
        const scoreChallenged = document.getElementById(`edit-set${i}-challenged`).value;
        if (scoreChallenger !== '' && scoreChallenged !== '') {
            sets.push([parseInt(scoreChallenger, 10), parseInt(scoreChallenged, 10)]);
        }
    }

    if (sets.length < 2) {
        editResultMessageDiv.textContent = 'Debe ingresar el resultado de al menos dos sets.';
        editResultMessageDiv.className = 'message error';
        return;
    }

    try {
        console.log("Intentando llamar a /api/matches/edit (backend para enviar resultado editado).");
        const response = await fetch(`/api/matches/${matchId}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sets: sets })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error desconocido al guardar los cambios.');
        }

        alert(data.message);
        closeEditMatchModal();
        // Recargar el historial del jugador y la lista de jugadores para ver los cambios de posición
        showOrganizerPlayerHistory(); 
        loadPlayersForOrganizer(); 

    } catch (error) {
        console.error('ERROR al enviar el resultado editado (fetch o JSON):', error);
        editResultMessageDiv.textContent = `Error: ${error.message}`;
        editResultMessageDiv.className = 'message error';
    }
}

// NUEVA FUNCIÓN: Carga los equipos de dobles para los selectores
async function loadDoublesTeamsForOrganizer() {
    try {
        const response = await fetch('/api/doubles_teams'); // Obtiene todos los equipos
        if (!response.ok) {
            throw new Error('Error al cargar equipos de dobles.');
        }
        allDoublesTeams = await response.json();
        
        const challengerTeamSelect = document.getElementById('challenger-team-select');
        const challengedTeamSelect = document.getElementById('challenged-team-select');

        challengerTeamSelect.innerHTML = '<option value="">Seleccione Equipo Desafiante</option>';
        challengedTeamSelect.innerHTML = '<option value="">Seleccione Equipo Desafiado</option>';

        allDoublesTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = team.id;
            option.textContent = `${team.team_name} (Puesto: ${team.current_position}, ${team.gender_category})`;
            challengerTeamSelect.appendChild(option.cloneNode(true));
            challengedTeamSelect.appendChild(option.cloneNode(true));
        });

    } catch (error) {
        console.error('Error en loadDoublesTeamsForOrganizer:', error);
        alert('No se pudieron cargar los equipos de dobles para el organizador.');
    }
}

// NUEVA FUNCIÓN: Valida un desafío de dobles
async function validateDoublesChallenge() {
    console.log("--- FUNCIÓN: validateDoublesChallenge() INICIADA ---");
    const challengerTeamId = document.getElementById('challenger-team-select').value;
    const challengedTeamId = document.getElementById('challenged-team-select').value;
    const validationMessage = document.getElementById('doubles-challenge-validation-message');
    const scoreForm = document.getElementById('doubles-score-entry-form');

    validationMessage.textContent = '';
    scoreForm.style.display = 'none';

    if (!challengerTeamId || !challengedTeamId || parseInt(challengerTeamId) === parseInt(challengedTeamId)) {
        validationMessage.textContent = 'Por favor, seleccione dos equipos de dobles diferentes.';
        validationMessage.className = 'message error';
        console.warn("Validación frontend fallida: IDs de equipos inválidos o iguales.");
        return;
    }

    try {
        console.log("Intentando llamar a /api/validate_doubles_challenge (backend para validación).");
        const response = await fetch('/api/validate_doubles_challenge', { // Necesitarás crear este endpoint en app.py
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ challengerTeamId: parseInt(challengerTeamId), challengedTeamId: parseInt(challengedTeamId) })
        });
        const data = await response.json();
        console.log("Datos recibidos de /api/validate_doubles_challenge:", data);

        validationMessage.textContent = data.message;
        if (data.valid) {
            validationMessage.className = 'message success';
            scoreForm.style.display = 'block';
            console.log("Validación backend exitosa. Llamando a proposeDoublesChallenge()...");
            await proposeDoublesChallenge(parseInt(challengerTeamId), parseInt(challengedTeamId));
        } else {
            validationMessage.className = 'message error';
            console.log("Validación backend fallida: Desafío de dobles no permitido.");
        }
    } catch (error) {
        console.error('ERROR en validateDoublesChallenge (fetch o JSON):', error);
        validationMessage.textContent = 'Error de conexión al validar el desafío de dobles.';
        validationMessage.className = 'message error';
    }
}

// NUEVA FUNCIÓN: Propone un desafío de dobles
async function proposeDoublesChallenge(challengerTeamId, challengedTeamId) {
    console.log(`--- FUNCIÓN: proposeDoublesChallenge() INICIADA con Equipo Desafiante=${challengerTeamId}, Equipo Desafiado=${challengedTeamId} ---`);
    try {
        const response = await fetch('/api/propose_doubles_challenge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ challengerTeamId, challengedTeamId })
        });
        const data = await response.json();

        if (!response.ok) {
            if (response.status === 409) {
                 alert(`Atención: ${data.error}`);
            } else {
                 throw new Error(data.error || 'Error desconocido al proponer el desafío de dobles.');
            }
        } else {
            alert(data.message);
            console.log("Desafío de dobles propuesto exitosamente. Recargando desafíos pendientes.");
            loadPendingDoublesChallengesForOrganizer(); // Recarga la lista de desafíos de dobles pendientes
        }
    } catch (error) {
        console.error('ERROR al proponer el desafío de dobles:', error);
        alert(`Error al proponer el desafío de dobles: ${error.message}`);
    }
}

// NUEVA FUNCIÓN: Carga y muestra los desafíos de dobles pendientes
async function loadPendingDoublesChallengesForOrganizer() {
    console.log("--- FUNCIÓN: loadPendingDoublesChallengesForOrganizer() INICIADA ---");
    const pendingDoublesChallengesListDiv = document.getElementById('pending-doubles-challenges-list'); 
    if (!pendingDoublesChallengesListDiv) {
        console.warn("Elemento 'pending-doubles-challenges-list' no encontrado en el DOM de organizer.html.");
        return;
    }

    pendingDoublesChallengesListDiv.innerHTML = '<p>Cargando desafíos de dobles pendientes...</p>';

    try {
        const response = await fetch('/api/pending_doubles_challenges'); 
        console.log(`Respuesta de /api/pending_doubles_challenges - Status: ${response.status}`);
        if (!response.ok) {
            throw new Error('Error al cargar los desafíos de dobles pendientes.');
        }
        const challenges = await response.json();
        console.log("Desafíos de dobles pendientes obtenidos:", challenges);

        pendingDoublesChallengesListDiv.innerHTML = '';

        if (challenges.length === 0) {
            pendingDoublesChallengesListDiv.innerHTML = '<p>No hay desafíos de dobles pendientes en este momento.</p>';
            return;
        }

        const ul = document.createElement('ul');
        ul.style.listStyle = 'none';
        ul.style.padding = '0';

        challenges.forEach(challenge => {
            const li = document.createElement('li');
            li.style.marginBottom = '10px';
            li.style.padding = '8px';
            li.style.border = '1px solid #ddd';
            li.style.borderRadius = '4px';
            li.style.backgroundColor = '#f9f9f9';

            li.innerHTML = `
                <span>
                    Desafío Dobles #${challenge.id}: <strong>${challenge.challenger_team_name}</strong> vs <strong>${challenge.challenged_team_name}</strong> 
                    (creado: ${new Date(challenge.created_at).toLocaleDateString()})
                </span>
                <button onclick="startDoublesMatchResultEntry(${challenge.id}, ${challenge.challenger_team_id}, ${challenge.challenged_team_id})" class="button" style="margin-left: 10px; background-color: #28a745; font-size: 0.8em; padding: 4px 8px;">
                    Ingresar Resultado
                </button>
                <button onclick="cancelPendingDoublesChallenge(${challenge.id})" class="button" style="margin-left: 5px; background-color: #ffc107; font-size: 0.8em; padding: 4px 8px;">
                    Cancelar
                </button>
            `;
            ul.appendChild(li);
        });
        pendingDoublesChallengesListDiv.appendChild(ul);

    } catch (error) {
        console.error('ERROR en loadPendingDoublesChallengesForOrganizer:', error);
        pendingDoublesChallengesListDiv.innerHTML = `<p style="color: red;">Error al cargar desafíos de dobles pendientes: ${error.message}</p>`;
    }
}

// NUEVA FUNCIÓN: Prepara el formulario de resultado de dobles
function startDoublesMatchResultEntry(challengeId, challengerTeamId, challengedTeamId) {
    console.log(`--- FUNCIÓN: startDoublesMatchResultEntry() INICIADA con Challenge ID=${challengeId}, Equipo Desafiante=${challengerTeamId}, Equipo Desafiado=${challengedTeamId} ---`);
    document.getElementById('challenger-team-select').value = challengerTeamId;
    document.getElementById('challenged-team-select').value = challengedTeamId;
    document.getElementById('doubles-score-entry-form').style.display = 'block';
    
    const hiddenDoublesChallengeIdInput = document.getElementById('hidden-doubles-challenge-id');
    if (hiddenDoublesChallengeIdInput) {
        hiddenDoublesChallengeIdInput.value = challengeId;
        console.log(`hidden-doubles-challenge-id establecido a: ${hiddenDoublesChallengeIdInput.value}`);
    } else {
        console.warn("Input oculto para challenge ID de dobles no encontrado. El resultado del partido no actualizará el estado del desafío.");
    }

    // Limpiar campos de sets
    document.getElementById('doubles-set1-challenger').value = '';
    document.getElementById('doubles-set1-challenged').value = '';
    document.getElementById('doubles-set2-challenger').value = '';
    document.getElementById('doubles-set2-challenged').value = '';
    document.getElementById('doubles-set3-challenger').value = '';
    document.getElementById('doubles-set3-challenged').value = '';
    document.getElementById('doubles-result-message').textContent = '';

    document.getElementById('doubles-score-entry-form').scrollIntoView({ behavior: 'smooth' });

    alert('Equipos seleccionados para ingresar resultado de dobles. Por favor, complete el marcador.');
}

// NUEVA FUNCIÓN: Envía el resultado del partido de dobles
async function submitDoublesMatchResult() {
    console.log("--- FUNCIÓN: submitDoublesMatchResult() INICIADA ---");
    const challengerTeamId = document.getElementById('challenger-team-select').value;
    const challengedTeamId = document.getElementById('challenged-team-select').value;
    const resultMessageDiv = document.getElementById('doubles-result-message');
    
    const hiddenDoublesChallengeId = document.getElementById('hidden-doubles-challenge-id').value;
    console.log(`Equipo Desafiante: ${challengerTeamId}, Equipo Desafiado: ${challengedTeamId}, Challenge ID (oculto): ${hiddenDoublesChallengeId}`);

    const sets = [];
    for (let i = 1; i <= 3; i++) {
        const scoreChallenger = document.getElementById(`doubles-set${i}-challenger`).value;
        const scoreChallenged = document.getElementById(`doubles-set${i}-challenged`).value;
        if (scoreChallenger !== '' && scoreChallenged !== '') {
            sets.push([parseInt(scoreChallenger, 10), parseInt(scoreChallenged, 10)]);
        }
    }

    if (sets.length < 2) {
        resultMessageDiv.textContent = 'Debe ingresar el resultado de al menos dos sets.';
        resultMessageDiv.className = 'message error';
        console.warn("Validación de sets de dobles fallida: Menos de 2 sets.");
        return;
    }

    try {
        console.log("Intentando llamar a /api/doubles_match_result (backend para enviar resultado de dobles).");
        const response = await fetch('/api/doubles_match_result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                challengerTeamId: parseInt(challengerTeamId),
                challengedTeamId: parseInt(challengedTeamId),
                sets: sets,
                challengeId: hiddenDoublesChallengeId ? parseInt(hiddenDoublesChallengeId) : null 
            })
        });
        const data = await response.json();
        console.log("Datos recibidos de /api/doubles_match_result:", data);

        if (response.ok) {
            alert(data.message);
            window.location.href = '/organizer'; // Recargar la página del organizador
        } else {
            resultMessageDiv.textContent = `Error: ${data.error || 'Ocurrió un error.'}`;
            resultMessageDiv.className = 'message error';
        }
    } catch (error) {
        console.error('ERROR al enviar el resultado de dobles (fetch o JSON):', error);
        resultMessageDiv.textContent = 'Error de conexión al enviar el resultado de dobles.';
        resultMessageDiv.className = 'message error';
    }
}

// NUEVA FUNCIÓN: Cancela un desafío de dobles pendiente
async function cancelPendingDoublesChallenge(challengeId) {
    if (!confirm(`¡ATENCIÓN! ¿Estás seguro de que quieres cancelar el desafío de dobles con ID ${challengeId}?`)) {
        return;
    }
    try {
        const response = await fetch(`/api/doubles_challenges/${challengeId}/cancel`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error desconocido al cancelar el desafío de dobles.');
        }
        alert(data.message);
        loadPendingDoublesChallengesForOrganizer(); // Recarga la lista
    } catch (error) {
        console.error('Error al cancelar el desafío de dobles:', error);
        alert(`Error al cancelar el desafío de dobles: ${error.message}`);
    }
}
