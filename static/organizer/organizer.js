// static/organizer/organizer.js

let allPlayers = [];
let allDoublesTeams = []; // Variable global para almacenar los equipos de dobles

// --- FUNCIONES DE UTILIDAD DE FECHAS (GLOBALES) ---
// Función para formatear la fecha a la que el input type="datetime-local" espera
function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Función para establecer el minDate en el campo de fin de torneo basado en el de inicio
function setMinTournamentEndDate() {
    const tournamentStartDateInput = document.getElementById('tournament-start-date');
    const tournamentEndDateInput = document.getElementById('tournament-end-date');

    if (tournamentStartDateInput && tournamentEndDateInput) { // Asegurarse de que los elementos existen
        if (tournamentStartDateInput.value) {
            tournamentEndDateInput.min = tournamentStartDateInput.value;
            // Si la fecha de fin actual es anterior a la nueva fecha mínima, ajustarla
            if (tournamentEndDateInput.value && tournamentEndDateInput.value < tournamentEndDateInput.min) {
                tournamentEndDateInput.value = tournamentEndDateInput.min;
            }
        } else {
            tournamentEndDateInput.min = ''; // No hay restricción si no hay fecha de inicio
        }
    }
}

// Función para predeterminar y bloquear fechas de registro
function setDefaultRegistrationDates() {
    const registrationStartDateInput = document.getElementById('registration-start-date');
    const registrationEndDateInput = document.getElementById('registration-end-date');

    if (registrationStartDateInput && registrationEndDateInput) { // Asegurarse de que los elementos existen
        const now = new Date();
        const nowFormatted = formatDateTimeLocal(now);

        // Solo predeterminar si los campos están vacíos
        if (!registrationStartDateInput.value) {
            registrationStartDateInput.value = nowFormatted;
        }
        
        const twelveHoursLater = new Date(now.getTime() + (12 * 60 * 60 * 1000)); // 12 horas después
        const twelveHoursLaterFormatted = formatDateTimeLocal(twelveHoursLater);
        
        if (!registrationEndDateInput.value) {
            registrationEndDateInput.value = twelveHoursLaterFormatted;
        }
        
        // Bloquear fechas anteriores en el campo de fin de registro
        registrationEndDateInput.min = registrationStartDateInput.value;
        // Si la fecha de fin actual es anterior a la nueva fecha mínima, ajustarla
        if (registrationEndDateInput.value && registrationEndDateInput.value < registrationEndDateInput.min) {
            registrationEndDateInput.value = registrationEndDateInput.min;
        }
    }
}
// --- FIN FUNCIONES DE UTILIDAD DE FECHAS ---


document.addEventListener('DOMContentLoaded', () => {
    // Inicializar la pestaña activa y cargar sus datos
    openTab(null, 'individual-management'); // Abrir la pestaña individual por defecto al cargar

    // Event Listeners para las fechas del torneo (se ejecutan una vez DOMContentLoaded)
    const tournamentStartDateInput = document.getElementById('tournament-start-date');
    const registrationStartDateInput = document.getElementById('registration-start-date');

    if (tournamentStartDateInput) {
        tournamentStartDateInput.addEventListener('change', setMinTournamentEndDate);
    }
    if (registrationStartDateInput) { // registrationEndDateInput.min ya se actualiza en setDefaultRegistrationDates
        registrationStartDateInput.addEventListener('change', () => {
            const registrationEndDateInput = document.getElementById('registration-end-date');
            if (registrationEndDateInput) {
                 registrationEndDateInput.min = registrationStartDateInput.value;
                 if (registrationEndDateInput.value && registrationEndDateInput.value < registrationStartDateInput.value) {
                    registrationEndDateInput.value = registrationStartDateInput.value;
                 }
            }
        });
    }

    // Configura el listener para el formulario de crear torneo
    const createTournamentForm = document.getElementById('create-tournament-form');
    if (createTournamentForm) {
        createTournamentForm.addEventListener('submit', createTournament); // El evento submit es en el formulario
    }

    // Asegurarse de que las fechas por defecto se carguen al iniciar, si la pestaña de torneos es la activa
    // Si individual-management es la activa por defecto, esta parte se llamará en openTab
    // Pero si se carga la página directamente en tournament-management, esto es útil
    // openTab ya llama a estas si tabName es 'tournament-management'
});


// NUEVA FUNCIÓN: Manejo de Pestañas
function openTab(evt, tabName) {
    let i, tabcontent, tabbuttons;

    // Obtener todos los elementos con class="tab-content" y ocultarlos
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
        tabcontent[i].classList.remove('active'); // Remover clase active
    }

    // Obtener todos los elementos con class="tab-button" y remover la clase "active"
    tabbuttons = document.getElementsByClassName("tab-button");
    for (i = 0; i < tabbuttons.length; i++) {
        tabbuttons[i].classList.remove("active");
    }

    // Mostrar el contenido de la pestaña actual y añadir "active" a la clase del botón que la abrió
    const selectedTabContent = document.getElementById(tabName);
    if (selectedTabContent) {
        selectedTabContent.style.display = "block";
        selectedTabContent.classList.add('active'); // Añadir clase active
    }
    if (evt) { // Si la función es llamada por un evento de clic (no en DOMContentLoaded)
        evt.currentTarget.classList.add("active");
    } else { // Si es llamada en DOMContentLoaded, activar el primer botón manualmente
        const initialActiveButton = document.querySelector(`.tab-button[onclick*="${tabName}"]`);
        if (initialActiveButton) {
            initialActiveButton.classList.add('active');
        }
    }

    // Lógica para cargar datos específicos de la pestaña
    switch (tabName) {
        case 'individual-management':
            loadPlayersForOrganizer(); // Recargar selectores de jugadores
            loadPendingChallengesForOrganizer(); // Recargar desafíos pendientes
            break;
        case 'doubles-management':
            loadDoublesTeamsForOrganizer(); // Cargar equipos de dobles para selectores
            loadPendingDoublesChallengesForOrganizer(); // Cargar desafíos de dobles pendientes
            break;
        case 'tournament-management':
            loadTournaments(); // Cargar la lista de torneos
            setDefaultRegistrationDates(); // Asegurarse de que las fechas por defecto se carguen al cambiar a esta pestaña
            setMinTournamentEndDate(); // Asegurarse de que la validación de fechas de torneo se aplique
            break;
        case 'settings-management':
            // Cargar ajustes si los hubiera
            break;
    }
}


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

        if (challengerSelect) challengerSelect.innerHTML = '<option value="">Seleccione un desafiante</option>';
        if (challengedSelect) challengedSelect.innerHTML = '<option value="">Seleccione un desafiado</option>';
        if (historySelect) historySelect.innerHTML = '<option value="">Seleccione un jugador</option>';

        allPlayers.forEach(player => {
            const option = document.createElement('option');
            option.value = player.id;
            option.textContent = `${player.first_name} ${player.last_name} (Puesto: ${player.current_position})`;
            if (challengerSelect) challengerSelect.appendChild(option.cloneNode(true));
            if (challengedSelect) challengedSelect.appendChild(option.cloneNode(true));
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

    const challengerId = challengerSelect ? challengerSelect.value : null;
    const challengedId = challengedSelect ? challengedSelect.value : null;
    console.log(`IDs seleccionados: Desafiante=${challengerId}, Desafiado=${challengedId}`);

    const validationMessage = document.getElementById('challenge-validation-message');
    const scoreForm = document.getElementById('score-entry-form');

    if (validationMessage) validationMessage.textContent = '';
    if (scoreForm) scoreForm.style.display = 'none';

    if (!challengerId || !challengedId || parseInt(challengerId) === parseInt(challengedId)) {
        if (validationMessage) {
            validationMessage.textContent = 'Por favor, seleccione dos jugadores diferentes.';
            validationMessage.className = 'message error';
        }
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

        if (validationMessage) validationMessage.textContent = data.message;
        if (data.valid) {
            if (validationMessage) validationMessage.className = 'message success';
            if (scoreForm) scoreForm.style.display = 'block';
            console.log("Validación backend exitosa. Llamando a proposeChallenge()...");
            await proposeChallenge(parseInt(challengerId), parseInt(challengedId));
        } else {
            if (validationMessage) validationMessage.className = 'message error';
            console.log("Validación backend fallida: Desafío no permitido.");
        }
    } catch (error) {
        console.error('ERROR en validateChallenge (fetch o JSON):', error);
        if (validationMessage) {
            validationMessage.textContent = 'Error de conexión al validar el desafío.';
            validationMessage.className = 'message error';
        }
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
                <button onclick="markRejectedChallenge(${challenge.id})" class="button button-danger" style="margin-left: 5px; font-size: 0.8em; padding: 4px 8px;">
                    Marcar Rechazado
                </button>
                <button onclick="markIgnoredChallenge(${challenge.id})" class="button button-warning" style="margin-left: 5px; font-size: 0.8em; padding: 4px 8px;">
                    Marcar Ignorado
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
    const challengerSelect = document.getElementById('challenger-select');
    const challengedSelect = document.getElementById('challenged-select');

    if (challengerSelect) challengerSelect.value = challengerId;
    if (challengedSelect) challengedSelect.value = challengedId;

    const scoreForm = document.getElementById('score-entry-form');
    if (scoreForm) scoreForm.style.display = 'block';

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

    const resultMessageDiv = document.getElementById('result-message');
    if (resultMessageDiv) resultMessageDiv.textContent = '';


    if (scoreForm) scoreForm.scrollIntoView({ behavior: 'smooth' });

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
        if (scoreChallenger !== '' && scoreChallenged !== '') {
            sets.push([parseInt(scoreChallenger, 10), parseInt(scoreChallenged, 10)]);
        }
    }

    if (sets.length < 2) {
        if (resultMessageDiv) {
            resultMessageDiv.textContent = 'Debe ingresar el resultado de al menos dos sets.';
            resultMessageDiv.className = 'message error';
        }
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
            loadPendingChallengesForOrganizer(); // Recargar desafíos individuales pendientes
            loadPendingDoublesChallengesForOrganizer(); // Recargar desafíos de dobles pendientes (por si acaso)
            loadPlayersForOrganizer(); // Recargar jugadores por si hay cambios de posición
            loadDoublesTeamsForOrganizer(); // Recargar equipos de dobles por si hay cambios de posición

            // Ocultar el formulario de ingreso de resultados individuales
            const scoreForm = document.getElementById('score-entry-form');
            if (scoreForm) scoreForm.style.display = 'none';

        } else {
            if (resultMessageDiv) {
                resultMessageDiv.textContent = `Error: ${data.error || 'Ocurrió un error.'}`;
                resultMessageDiv.className = 'message error';
            }
        }
    } catch (error) {
        console.error('ERROR al enviar el resultado (fetch o JSON):', error);
        if (resultMessageDiv) {
            resultMessageDiv.textContent = 'Error de conexión al enviar el resultado.';
            resultMessageDiv.className = 'message error';
        }
    }
}

// FUNCIÓN: Muestra el historial de un jugador en el panel del organizador
async function showOrganizerPlayerHistory() {
    console.log("--- FUNCIÓN: showOrganizerPlayerHistory() INICIADA ---");
    const playerId = document.getElementById('history-player-select').value;
    const historyList = document.getElementById('organizer-history-list');

    if (!historyList) {
        console.warn("Elemento 'organizer-history-list' no encontrado en el DOM.");
        return;
    }

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
async function resetLeaderboard() { // Antes: resetLeaderboard
    const resetMessage = document.getElementById('reset-message');
    if (!confirm('¿Estás seguro de que quieres reiniciar la tabla de posiciones general? Esto actualizará el "Puesto Inicial" de todos a su puesto actual y reiniciará los puntos.')) {
        return;
    }
    try {
        const response = await fetch('/api/reset_leaderboard', { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            if (resetMessage) {
                resetMessage.textContent = data.message;
                resetMessage.className = 'message success';
            }
            loadPlayersForOrganizer(); // Recargar jugadores para ver cambios
        } else {
            if (resetMessage) {
                resetMessage.textContent = `Error: ${data.error}`;
                resetMessage.className = 'message error';
            }
        }
    } catch (error) {
        console.error('Error de conexión al reiniciar la tabla:', error);
        if (resetMessage) {
            resetMessage.textContent = 'Error de conexión al reiniciar la tabla.';
            resetMessage.className = 'message error';
        }
    }
}

// NUEVA FUNCIÓN: Reinicia el ciclo de actividad
async function resetActivityCycle() { // Antes: resetCycleActivity (estaba en app.py, ahora es el cliente que la llama)
    const resetCycleMessage = document.getElementById('reset-cycle-message'); // Nuevo ID de mensaje
    if (!confirm('¡ATENCIÓN! ¿Estás seguro de que quieres reiniciar el ciclo de actividad global? Esto pondrá a CERO los rechazos del ciclo actual y recalculará los estados de actividad de TODOS los jugadores en el Ranking Maestro.')) {
        return;
    }
    try {
        const response = await fetch('/api/reset_cycle_activity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (response.ok) {
            if (resetCycleMessage) {
                resetCycleMessage.textContent = data.message;
                resetCycleMessage.className = 'message success';
            }
            alert(data.message);
            loadPlayersForOrganizer(); // Recargar jugadores para actualizar estados de actividad
        } else {
            if (resetCycleMessage) {
                resetCycleMessage.textContent = `Error: ${data.error || 'Ocurrió un error desconocido al reiniciar el ciclo.'}`;
                resetCycleMessage.className = 'message error';
            }
            console.error('Error al reiniciar el ciclo de actividad:', data.error);
        }
    } catch (error) {
        console.error('ERROR de conexión al reiniciar el ciclo de actividad:', error);
        if (resetCycleMessage) {
            resetCycleMessage.textContent = 'Error de conexión con el servidor al intentar reiniciar el ciclo de actividad.';
            resetCycleMessage.className = 'message error';
        }
    }
}


// FUNCIÓN: Abre el modal de edición de partido
async function openEditMatchModal(matchId) {
    const modal = document.getElementById('edit-match-modal');
    const challengerNameSpan = document.getElementById('edit-challenger-name');
    const challengedNameSpan = document.getElementById('edit-challenged-name');
    const editMatchIdInput = document.getElementById('edit-match-id');
    const editResultMessageDiv = document.getElementById('edit-result-message');

    if (editResultMessageDiv) editResultMessageDiv.textContent = ''; // Limpiar mensajes previos

    try {
        // Obtener detalles del partido desde el backend
        const response = await fetch(`/api/matches/${matchId}`);
        if (!response.ok) {
            throw new Error('No se pudieron cargar los detalles del partido para editar.');
        }
        const match = await response.json();
        console.log("Detalles del partido para editar:", match);

        // Rellenar el modal con los datos del partido
        if (editMatchIdInput) editMatchIdInput.value = match.id;
        if (challengerNameSpan) challengerNameSpan.textContent = match.challenger_name;
        if (challengedNameSpan) challengedNameSpan.textContent = match.challenged_name;

        // Limpiar campos de sets
        for (let i = 1; i <= 3; i++) {
            const setChallenger = document.getElementById(`edit-set${i}-challenger`);
            const setChallenged = document.getElementById(`edit-set${i}-challenged`);
            if (setChallenger) setChallenger.value = '';
            if (setChallenged) setChallenged.value = '';
        }

        // Rellenar sets existentes
        match.sets.forEach((set, index) => {
            if (index < 3) {
                const setChallenger = document.getElementById(`edit-set${index + 1}-challenger`);
                const setChallenged = document.getElementById(`edit-set${index + 1}-challenged`);
                if (setChallenger) setChallenger.value = set[0];
                if (setChallenged) setChallenged.value = set[1];
            }
        });

        if (modal) modal.style.display = 'flex'; // Mostrar el modal
    } catch (error) {
        console.error('Error al abrir el modal de edición:', error);
        alert(`Error al cargar el partido para editar: ${error.message}`);
    }
}

// FUNCIÓN: Cierra el modal de edición de partido
function closeEditMatchModal() {
    const modal = document.getElementById('edit-match-modal');
    if (modal) modal.style.display = 'none';
    const editResultMessageDiv = document.getElementById('edit-result-message');
    if (editResultMessageDiv) editResultMessageDiv.textContent = ''; // Limpiar mensaje
}

// FUNCIÓN: Envía los resultados editados al backend
async function submitEditedMatchResult() {
    console.log("--- FUNCIÓN: submitEditedMatchResult() INICIADA ---");
    const matchIdInput = document.getElementById('edit-match-id');
    const matchId = matchIdInput ? matchIdInput.value : null;
    const editResultMessageDiv = document.getElementById('edit-result-message');
    if (editResultMessageDiv) editResultMessageDiv.textContent = ''; // Limpiar mensajes previos

    if (!matchId) {
        if (editResultMessageDiv) {
            editResultMessageDiv.textContent = 'ID de partido no encontrado para editar.';
            editResultMessageDiv.className = 'message error';
        }
        console.warn("Match ID not found for editing.");
        return;
    }

    const sets = [];
    for (let i = 1; i <= 3; i++) {
        const scoreChallenger = document.getElementById(`edit-set${i}-challenger`).value;
        const scoreChallenged = document.getElementById(`edit-set${i}-challenged`).value;
        if (scoreChallenger !== '' && scoreChallenged !== '') {
            sets.push([parseInt(scoreChallenger, 10), parseInt(scoreChallenged, 10)]);
        }
    }

    if (sets.length < 2) {
        if (editResultMessageDiv) {
            editResultMessageDiv.textContent = 'Debe ingresar el resultado de al menos dos sets.';
            editResultMessageDiv.className = 'message error';
        }
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
        if (editResultMessageDiv) {
            editResultMessageDiv.textContent = `Error: ${error.message}`;
            editResultMessageDiv.className = 'message error';
        }
    }
}

// NUEVA FUNCIÓN: Carga los equipos de dobles para los selectores
async function loadDoublesTeamsForOrganizer() {
    try {
        const challengerTeamSelect = document.getElementById('challenger-team-select');
        const challengedTeamSelect = document.getElementById('challenged-team-select');

        if (challengerTeamSelect) challengerTeamSelect.innerHTML = '<option value="">Seleccione Equipo Desafiante</option>';
        if (challengedTeamSelect) challengedTeamSelect.innerHTML = '<option value="">Seleccione Equipo Desafiado</option>';


        // Endpoint para obtener TODOS los equipos GLOBALES de la tabla Teams
        const response = await fetch('/api/global_doubles_teams'); // NECESITARÁS CREAR ESTE ENDPOINT EN app.py
        if (!response.ok) {
            // Manejar 404 específicamente si el backend lo envía para 'no teams found'
            if (response.status === 404) {
                alert('No hay equipos de dobles globales registrados.');
                return;
            }
            throw new Error('Error al cargar equipos de dobles globales.');
        }
        allDoublesTeams = await response.json(); // Estos serán los equipos de la tabla Teams global

        allDoublesTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = team.id; // El ID del equipo GLOBAL
            option.textContent = `${team.team_name} (${team.gender_category})`; // Solo el nombre y género
            if (challengerTeamSelect) challengerTeamSelect.appendChild(option.cloneNode(true));
            if (challengedTeamSelect) challengedTeamSelect.appendChild(option.cloneNode(true));
        });

    } catch (error) {
        console.error('Error en loadDoublesTeamsForOrganizer:', error);
        alert('No se pudieron cargar los equipos de dobles para el organizador.');
    }
}

// NUEVA FUNCIÓN: Valida un desafío de dobles
async function validateDoublesChallenge() {
    console.log("--- FUNCIÓN: validateDoublesChallenge() INICIADA ---");
    const challengerTeamSelect = document.getElementById('challenger-team-select');
    const challengedTeamSelect = document.getElementById('challenged-team-select');

    const challengerTeamId = challengerTeamSelect ? challengerTeamSelect.value : null;
    const challengedTeamId = challengedTeamSelect ? challengedTeamSelect.value : null;

    const validationMessage = document.getElementById('doubles-challenge-validation-message');
    const scoreForm = document.getElementById('doubles-score-entry-form');

    if (validationMessage) validationMessage.textContent = '';
    if (scoreForm) scoreForm.style.display = 'none';

    if (!challengerTeamId || !challengedTeamId || parseInt(challengerTeamId) === parseInt(challengedTeamId)) {
        if (validationMessage) {
            validationMessage.textContent = 'Por favor, seleccione dos equipos de dobles diferentes.';
            validationMessage.className = 'message error';
        }
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

        if (validationMessage) validationMessage.textContent = data.message;
        if (data.valid) {
            if (validationMessage) validationMessage.className = 'message success';
            if (scoreForm) scoreForm.style.display = 'block';
            console.log("Validación backend exitosa. Llamando a proposeDoublesChallenge()...");
            await proposeDoublesChallenge(parseInt(challengerTeamId), parseInt(challengedTeamId));
        } else {
            if (validationMessage) validationMessage.className = 'message error';
            console.log("Validación backend fallida: Desafío de dobles no permitido.");
        }
    } catch (error) {
        console.error('ERROR en validateDoublesChallenge (fetch o JSON):', error);
        if (validationMessage) {
            validationMessage.textContent = 'Error de conexión al validar el desafío de dobles.';
            validationMessage.className = 'message error';
        }
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
        console.log("DEBUG: Desafíos de dobles pendientes obtenidos (organizer) DESPUÉS DE CARGAR RESULTADO:", challenges);

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
                <button onclick="markRejectedDoublesChallenge(${challenge.id})" class="button button-danger" style="margin-left: 5px; font-size: 0.8em; padding: 4px 8px;">
                    Marcar Rechazado
                </button>
                <button onclick="markIgnoredDoublesChallenge(${challenge.id})" class="button button-warning" style="margin-left: 5px; font-size: 0.8em; padding: 4px 8px;">
                    Marcar Ignorado
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

    console.log(`DEBUG: startDoublesMatchResultEntry - Challenge ID recibido del onclick: ${challengeId}`);

    const challengerTeamSelect = document.getElementById('challenger-team-select');
    const challengedTeamSelect = document.getElementById('challenged-team-select');

    if (challengerTeamSelect) challengerTeamSelect.value = challengerTeamId;
    if (challengedTeamSelect) challengedTeamSelect.value = challengedTeamId;

    const doublesScoreForm = document.getElementById('doubles-score-entry-form');
    if (doublesScoreForm) doublesScoreForm.style.display = 'block';

    const hiddenDoublesChallengeIdInput = document.getElementById('hidden-doubles-challenge-id');
    if (hiddenDoublesChallengeIdInput) {
        hiddenDoublesChallengeIdInput.value = challengeId;
        console.log(`DEBUG: hidden-doubles-challenge-id establecido a: ${hiddenDoublesChallengeIdInput.value}`);
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

    const doublesResultMessageDiv = document.getElementById('doubles-result-message');
    if (doublesResultMessageDiv) doublesResultMessageDiv.textContent = '';


    if (doublesScoreForm) doublesScoreForm.scrollIntoView({ behavior: 'smooth' });

    alert('Equipos seleccionados para ingresar resultado de dobles. Por favor, complete el marcador.');
}


// NUEVA FUNCIÓN: Envía el resultado del partido de dobles
async function submitDoublesMatchResult() {
    console.log("--- FUNCIÓN: submitDoublesMatchResult() INICIADA ---");
    const challengerTeamId = document.getElementById('challenger-team-select').value;
    const challengedTeamId = document.getElementById('challenged-team-select').value;
    const resultMessageDiv = document.getElementById('doubles-result-message');

    const hiddenDoublesChallengeIdInput = document.getElementById('hidden-doubles-challenge-id');
    const hiddenDoublesChallengeId = hiddenDoublesChallengeIdInput ? hiddenDoublesChallengeIdInput.value : null;
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
        if (resultMessageDiv) {
            resultMessageDiv.textContent = 'Debe ingresar el resultado de al menos dos sets.';
            resultMessageDiv.className = 'message error';
        }
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
            // Recargar las listas sin recargar la página completa
            loadPendingDoublesChallengesForOrganizer();
            loadPlayersForOrganizer(); // Recargar jugadores por si hay cambios de posición
            loadDoublesTeamsForOrganizer(); // Recargar equipos de dobles por si hay cambios de posición

            // Ocultar el formulario de ingreso de resultados de dobles
            const doublesScoreForm = document.getElementById('doubles-score-entry-form');
            if (doublesScoreForm) doublesScoreForm.style.display = 'none';

        } else {
            if (resultMessageDiv) {
                resultMessageDiv.textContent = `Error: ${data.error || 'Ocurrió un error.'}`;
                resultMessageDiv.className = 'message error';
            }
        }
    } catch (error) {
        console.error('ERROR al enviar el resultado de dobles (fetch o JSON):', error);
        if (resultMessageDiv) {
            resultMessageDiv.textContent = 'Error de conexión al enviar el resultado de dobles.';
            resultMessageDiv.className = 'message error';
        }
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

// NUEVA FUNCIÓN: Marca un desafío como rechazado
async function markRejectedChallenge(challengeId) {
    if (!confirm(`¿Estás seguro de que quieres marcar el desafío #${challengeId} como RECHAZADO?`)) {
        return;
    }
    try {
        const response = await fetch(`/api/challenges/${challengeId}/reject`, { // Endpoint a crear en el backend
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error desconocido al marcar como rechazado.');
        }
        alert(data.message);
        loadPendingChallengesForOrganizer(); // Recargar la lista de desafíos
    } catch (error) {
        console.error('Error al marcar desafío como rechazado:', error);
        alert(`Error: ${error.message}`);
    }
}

// NUEVA FUNCIÓN: Marca un desafío como ignorado
async function markIgnoredChallenge(challengeId) {
    if (!confirm(`¿Estás seguro de que quieres marcar el desafío #${challengeId} como IGNORADO?`)) {
        return;
    }
    try {
        const response = await fetch(`/api/challenges/${challengeId}/ignore`, { // Endpoint a crear en el backend
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error desconocido al marcar como ignorado.');
        }
        alert(data.message);
        loadPendingChallengesForOrganizer(); // Recargar la lista de desafíos
    } catch (error) {
        console.error('Error al marcar desafío como ignorado:', error);
        alert(`Error: ${error.message}`);
    }
}

// NUEVA FUNCIÓN: Marca un desafío de dobles como rechazado
async function markRejectedDoublesChallenge(challengeId) {
    if (!confirm(`¿Estás seguro de que quieres marcar el desafío de dobles #${challengeId} como RECHAZADO? Esto penalizará a los jugadores del equipo desafiado.`)) {
        return;
    }
    try {
        const response = await fetch(`/api/doubles_challenges/${challengeId}/reject`, { // Endpoint a crear en el backend
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error desconocido al marcar como rechazado.');
        }
        alert(data.message);
        loadPendingDoublesChallengesForOrganizer(); // Recargar la lista de desafíos de dobles
    }
    catch (error) {
        console.error('Error al marcar desafío de dobles como rechazado:', error);
        alert(`Error: ${error.message}`);
    }
}

// NUEVA FUNCIÓN: Marca un desafío de dobles como ignorado
async function markIgnoredDoublesChallenge(challengeId) {
    if (!confirm(`¿Estás seguro de que quieres marcar el desafío de dobles #${challengeId} como IGNORADO? Esto compensará a los jugadores del equipo desafiante.`)) {
        return;
    }
    try {
        const response = await fetch(`/api/doubles_challenges/${challengeId}/ignore`, { // Endpoint a crear en el backend
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error desconocido al marcar como ignorado.');
        }
        alert(data.message);
        loadPendingDoublesChallengesForOrganizer(); // Recargar la lista de desafíos de dobles
    } catch (error) {
        console.error('Error al marcar desafío de dobles como ignorado:', error);
        alert(`Error: ${error.message}`);
    }
}

// --- NUEVAS FUNCIONES PARA GESTIÓN DE TORNEOS ---

// FUNCIÓN: Crear Torneo
async function createTournament(event) {
    event.preventDefault(); // Prevenir el envío tradicional del formulario

    // Campos obligatorios
    const nameInput = document.getElementById('tournament-name');
    const typeSelect = document.getElementById('tournament-type');
    const startDateInput = document.getElementById('tournament-start-date');
    const endDateInput = document.getElementById('tournament-end-date');

    const name = nameInput ? nameInput.value.trim() : null;
    const type = typeSelect ? typeSelect.value : null;
    const startDate = startDateInput ? startDateInput.value : null; // YYYY-MM-DD
    const endDate = endDateInput ? endDateInput.value : null;     // YYYY-MM-DD

    const messageDiv = document.getElementById('create-tournament-message');
    if (messageDiv) messageDiv.textContent = ''; // Limpiar mensajes anteriores

    // Validaciones de frontend antes de enviar
    if (!name || !type || !startDate || !endDate) {
        if (messageDiv) {
            messageDiv.textContent = 'Nombre, Tipo, Fecha de Inicio y Fecha de Fin del torneo son obligatorios.';
            messageDiv.className = 'message error';
        }
        console.error("Faltan campos obligatorios para crear torneo.");
        return;
    }
    if (new Date(startDate) > new Date(endDate)) {
        if (messageDiv) {
            messageDiv.textContent = 'La fecha de inicio del torneo no puede ser posterior a la fecha de fin.';
            messageDiv.className = 'message error';
        }
        console.error("Fechas de torneo inválidas: inicio posterior a fin.");
        return;
    }


    // Campos opcionales (con verificaciones de existencia)
    const regStartDateElement = document.getElementById('registration-start-date');
    const regEndDateElement = document.getElementById('registration-end-date');
    const descriptionElement = document.getElementById('tournament-description');
    const rulesUrlElement = document.getElementById('tournament-rules-url');
    const categoryElement = document.getElementById('tournament-category');
    const maxSlotsElement = document.getElementById('tournament-max-slots');
    const costElement = document.getElementById('tournament-cost');
    const requirementsElement = document.getElementById('tournament-requirements');
    const locationElement = document.getElementById('tournament-location');
    const isPublishedElement = document.getElementById('tournament-is-published');

    // Función auxiliar para formatear datetime-local a YYYY-MM-DD HH:MM:SS
    const formatDateTimeToBackend = (dtLocalString) => {
        if (!dtLocalString) return null; // Si está vacío, enviar null
        return dtLocalString.replace('T', ' ') + ':00'; // Añadir segundos
    };

    const payload = {
        name: name,
        type: type,
        // El backend espera YYYY-MM-DD HH:MM:SS para parsear, pero luego ignora la hora para start_date/end_date de torneo
        start_date: startDate + ' 00:00:00',
        end_date: endDate + ' 00:00:00',
        
        registration_start_date: regStartDateElement ? formatDateTimeToBackend(regStartDateElement.value) : null,
        registration_end_date: regEndDateElement ? formatDateTimeToBackend(regEndDateElement.value) : null,
        
        description: descriptionElement ? descriptionElement.value.trim() : null,
        rules_url: rulesUrlElement ? rulesUrlElement.value.trim() : null,
        category: categoryElement ? categoryElement.value.trim() : null,
        max_slots: maxSlotsElement ? parseInt(maxSlotsElement.value) || 0 : 0, // Asegurar que sea número o 0
        cost: costElement ? parseFloat(costElement.value) || 0.0 : 0.0, // Asegurar que sea número o 0.0
        requirements: requirementsElement ? requirementsElement.value.trim() : null,
        location: locationElement ? locationElement.value.trim() : null,
        is_published: isPublishedElement ? (isPublishedElement.checked ? 1 : 0) : 0 // Checkbox a 1 o 0
    };

    console.log("Datos a enviar para crear torneo:", payload); // DEBUG

    try {
        const response = await fetch('/api/tournaments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (response.ok) {
            if (messageDiv) {
                messageDiv.textContent = data.message;
                messageDiv.className = 'message success';
            }
            alert('Torneo creado: ' + data.message);
            // Limpiar el formulario después del éxito
            const createTournamentForm = document.getElementById('create-tournament-form');
            if (createTournamentForm) {
                createTournamentForm.reset();
                setDefaultRegistrationDates(); // Restablecer fechas de registro por defecto
                setMinTournamentEndDate(); // Asegurarse de que la fecha de fin se resetee
            }
            loadTournaments(); // Recargar la lista de torneos
        } else {
            if (messageDiv) {
                messageDiv.textContent = `Error: ${data.error || 'Ocurrió un error desconocido.'}`;
                messageDiv.className = 'message error';
            }
            console.error('Error al crear torneo:', data.error);
        }
    } catch (error) {
        console.error('ERROR de conexión al crear torneo:', error);
        if (messageDiv) {
            messageDiv.textContent = 'Error de conexión con el servidor al intentar crear el torneo.';
            messageDiv.className = 'message error';
        }
    }
}

async function manageTournamentStatus(tournamentId, tournamentName, currentStatus, tournamentType) {
    const validStatuses = ['registration_open', 'in_progress', 'completed', 'cancelled'];
    let statusPrompt = `Gestionar estado para: ${tournamentName} (Actual: ${currentStatus.charAt(0).toUpperCase() + currentStatus.slice(1)})\n`;
    statusPrompt += `Tipos de estado disponibles: ${validStatuses.join(', ')}\n`;
    statusPrompt += `Introduce el nuevo estado:`;

    const newStatus = prompt(statusPrompt);

    if (newStatus === null || !validStatuses.includes(newStatus.toLowerCase())) {
        alert('Operación cancelada o estado no válido. El estado debe ser: ' + validStatuses.join(', '));
        return;
    }

    if (!confirm(`¿Estás seguro de cambiar el estado de "${tournamentName}" a "${newStatus.toLowerCase()}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/tournaments/${tournamentId}/update_status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus.toLowerCase() })
        });
        const data = await response.json();

        if (response.ok) {
            alert(data.message);
            loadTournaments(); // Recargar la lista para ver el estado actualizado
        } else {
            alert(`Error al actualizar estado: ${data.error || 'Ocurrió un error desconocido.'}`);
            console.error('Error al actualizar estado del torneo:', data.error);
        }
    } catch (error) {
        console.error('ERROR de conexión al actualizar estado del torneo:', error);
        alert(`Error de conexión: ${error.message}`);
    }
}

// FUNCIÓN: Cargar Torneos (PARA EL ORGANIZADOR)
async function loadTournaments() {
    const tournamentsListDiv = document.getElementById('tournaments-list');
    if (!tournamentsListDiv) return; // Asegurarse de que el div exista

    tournamentsListDiv.innerHTML = '<p>Cargando torneos existentes...</p>';

    try {
        // En el panel del organizador, no filtramos por is_published, queremos ver todos
        const response = await fetch('/api/tournaments?include_unpublished=true'); // NUEVO PARAMETRO
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al cargar la lista de torneos.');
        }
        const tournaments = await response.json();

        tournamentsListDiv.innerHTML = ''; // Limpiar mensaje de carga

        if (tournaments.length === 0) {
            tournamentsListDiv.innerHTML = '<p>No hay torneos registrados aún.</p>';
            return;
        }

        let tournamentsHtml = '<ul>';
        tournaments.forEach(tournament => {
            // Asegurarse de que las propiedades existan antes de usarlas
            const startDate = tournament.start_date ? new Date(tournament.start_date).toLocaleDateString() : 'N/A';
            const endDate = tournament.end_date ? new Date(tournament.end_date).toLocaleDateString() : 'N/A';
            const regStartDate = tournament.registration_start_date ? new Date(tournament.registration_start_date).toLocaleDateString() : 'N/A';
            const regEndDate = tournament.registration_end_date ? new Date(tournament.registration_end_date).toLocaleDateString() : 'N/A';
            const description = tournament.description || 'Sin descripción';
            const rulesUrl = tournament.rules_url || '';
            const category = tournament.category || 'N/A';
            const maxSlots = tournament.max_slots > 0 ? `${tournament.max_slots} cupos` : 'Ilimitados';
            const cost = typeof tournament.cost === 'number' ? `$${tournament.cost.toFixed(2)}` : 'N/A';
            const requirements = tournament.requirements || 'Ninguno';
            const location = tournament.location || 'N/A';
            const organizerName = tournament.organizer_name || 'N/A'; // Necesitarás que el backend envíe esto

            tournamentsHtml += `
                <li>
                    <strong>${tournament.name}</strong> (${tournament.type.replace(/_/g, ' ').toUpperCase()})<br>
                    Estado: ${tournament.status.charAt(0).toUpperCase() + tournament.status.slice(1)}
                    ${tournament.is_published ? '<span style="color: green;">(PUBLICADO)</span>' : '<span style="color: orange;">(NO PUBLICADO)</span>'}<br>
                    Creado por: ${organizerName}<br>
                    Periodo del Torneo: ${startDate} - ${endDate} <br>
                    Periodo de Registro: ${regStartDate} - ${regEndDate} <br>
                    Categoría: ${category} | Cupos: ${maxSlots} | Costo: ${cost}<br>
                    Requisitos: ${requirements} | Ubicación: ${location}<br>
                    ${description ? `<em>Descripción: ${description}</em><br>` : ''}
                    ${rulesUrl ? `<a href="${rulesUrl}" target="_blank">Reglas del Torneo</a><br>` : ''}
                    
                    <button class="button button-warning" style="font-size: 0.8em; padding: 4px 8px; margin-top: 5px;">Editar</button>
                    <button class="button button-info" style="font-size: 0.8em; padding: 4px 8px; margin-top: 5px;">Participantes</button>

                    <button onclick="manageTournamentStatus(${tournament.id}, '${tournament.name}', '${tournament.status}', '${tournament.type}')"
                            class="button" style="background-color: #6c757d; font-size: 0.8em; padding: 4px 8px; margin-top: 5px;">
                        Gestionar Estado
                    </button>

                    ${tournament.is_active ? '<span style="margin-left: 10px; font-weight: bold; color: green;">(ACTIVO PIRÁMIDE)</span>' : ''}
                </li>
            `;
        });
        tournamentsHtml += '</ul>';
        tournamentsListDiv.innerHTML = tournamentsHtml;

    } catch (error) {
        console.error('Error en loadTournaments (Organizador):', error);
        tournamentsListDiv.innerHTML = `<p style="color: red;">Error al cargar torneos: ${error.message}</p>`;
    }
}


// Función dummy para mostrar mensajes flash si no la tienes ya en organizer.js
// Asegúrate de que tu HTML tenga un div con id="flash-messages"
function showFlashMessage(message, category) {
    const flashDiv = document.getElementById('flash-messages');
    if (flashDiv) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${category}`;
        alertDiv.textContent = message;
        flashDiv.innerHTML = ''; // Limpiar mensajes anteriores
        flashDiv.appendChild(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000); // Ocultar después de 5 segundos
    } else {
        console.warn("Elemento #flash-messages no encontrado para mostrar el flash.");
    }
}