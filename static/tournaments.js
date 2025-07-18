// static/tournaments.js

document.addEventListener('DOMContentLoaded', function() {
    const tournamentsListDiv = document.getElementById('tournaments-list');
    const noTournamentsMessage = document.getElementById('no-tournaments-found');
    const statusFilter = document.getElementById('tournament-status-filter');
    const typeFilter = document.getElementById('tournament-type-filter');
    const applyFiltersBtn = document.getElementById('apply-filters-btn');

    // Constantes para el modal de dobles (en tournaments.html)
    const doublesEnrollmentModal = document.getElementById('doubles-enrollment-modal');
    const modalTournamentNameSpan = document.getElementById('modal-tournament-name');
    const modalTournamentIdInput = document.getElementById('modal-tournament-id');
    const modalTournamentTypeInput = document.getElementById('modal-tournament-type');
    const existingTeamSelect = document.getElementById('existing-team-select');
    const enrollWithExistingTeamBtn = document.getElementById('enroll-with-existing-team-btn');
    const partnerSearchInputModal = document.getElementById('partner-search-input-modal');
    const searchPartnersModalBtn = document.getElementById('search-partners-modal-btn');
    const partnerSearchResultsModalDiv = document.getElementById('partner-search-results-modal');
    const doublesEnrollmentMessageDiv = document.getElementById('doubles-enrollment-message');
    const closeDoublesEnrollmentModalBtn = document.querySelector('#doubles-enrollment-modal .close-button');


    // Función para mostrar mensajes flash
    function showFlashMessage(message, category) {
        const flashDiv = document.getElementById('flash-messages');
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${category}`;
        alertDiv.textContent = message;
        flashDiv.innerHTML = ''; // Limpiar mensajes anteriores
        flashDiv.appendChild(alertDiv);
        setTimeout(() => alertDiv.remove(), 5000); // Ocultar después de 5 segundos
    }

    // Función para cargar y renderizar torneos
    async function loadTournaments() {
        tournamentsListDiv.innerHTML = '<p>Cargando torneos...</p>';
        noTournamentsMessage.style.display = 'none';

        const selectedStatus = statusFilter.value;
        const selectedType = typeFilter.value;

        let url = '/api/obtener_todos_los_torneos_disponibles'; // <<-- ¡NUEVA URL!
        const params = [];
        if (selectedStatus) {
            params.push(`status=${selectedStatus}`);
        }
        if (selectedType) {
            params.push(`type=${selectedType}`);
        }
        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const tournaments = await response.json();

            tournamentsListDiv.innerHTML = ''; // Limpiar mensaje de carga

            if (tournaments.length === 0) {
                noTournamentsMessage.style.display = 'block';
            } else {
                tournaments.forEach(tournament => {
                    const tournamentCard = document.createElement('div');
                    tournamentCard.className = 'tournament-card';
                    tournamentCard.innerHTML = `
                        <h3>${tournament.name} (${tournament.type.replace(/_/g, ' ').toUpperCase()})</h3>
                        <p><strong>Descripción:</strong> ${tournament.description || 'Sin descripción'}</p>
                        <p><strong>Fechas:</strong> ${new Date(tournament.start_date).toLocaleDateString()} - ${new Date(tournament.end_date).toLocaleDateString()}</p>
                        <p><strong>Inscripciones:</strong> ${new Date(tournament.registration_start_date).toLocaleDateString()} - ${new Date(tournament.registration_end_date).toLocaleDateString()}</p>
                        <p><strong>Costo:</strong> $${(tournament.cost || 0).toFixed(2)}</p>
                        <p><strong>Categoría:</strong> ${tournament.category || 'Abierta'}</p>
                        <p><strong>Ubicación:</strong> ${tournament.location || 'No especificada'}</p>
                        <p><strong>Estado:</strong> ${tournament.registration_info}</p>
                        <button class="register-btn" data-tournament-id="${tournament.id}" data-tournament-type="${tournament.type}"
                                ${!tournament.can_register ? 'disabled' : ''}>
                            ${tournament.is_registered ? 'Ya Inscrito' : 'Inscribirse'}
                        </button>
                    `;
                    tournamentsListDiv.appendChild(tournamentCard);
                });

                // Añadir event listeners a los botones de inscripción
                document.querySelectorAll('.register-btn').forEach(button => {
                    button.addEventListener('click', handleRegisterClick);
                });
            }

        } catch (error) {
            console.error('Error al cargar torneos:', error);
            tournamentsListDiv.innerHTML = '<p class="error-message">Error al cargar los torneos. Intenta de nuevo más tarde.</p>';
        }
    }

    // Función para manejar el clic en el botón de inscripción (modificada)
    async function handleRegisterClick(event) {
        const button = event.target;
        const tournamentId = button.dataset.tournamentId;
        const tournamentType = button.dataset.tournamentType; // Obtener el tipo de torneo

        if (button.disabled) {
            return;
        }

        // Si es un torneo de dobles, abrir el modal específico
        if (tournamentType.startsWith('pyramid_doubles_') || tournamentType.startsWith('satellite_doubles_')) {
            // Obtenemos la info del torneo directamente del HTML para el modal
            const tournamentName = button.closest('.tournament-card').querySelector('h3').textContent.split('(')[0].trim();
            const tournamentInfoForModal = {
                id: tournamentId,
                name: tournamentName,
                type: tournamentType
            };
            openDoublesEnrollmentModal(tournamentInfoForModal);
        } else {
            // Si es individual, proceder con la inscripción directa como antes
            button.disabled = true;
            button.textContent = 'Inscribiendo...';
            try {
                const response = await fetch('/register_for_tournament', { // Endpoint de inscripción individual
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tournament_id: tournamentId })
                });
                const result = await response.json();
                if (response.ok) {
                    showFlashMessage(result.message, 'success');
                    button.textContent = 'Ya Inscrito';
                    button.disabled = true;
                } else {
                    showFlashMessage(result.error || 'Error al inscribirse.', 'error');
                    button.textContent = 'Inscribirse';
                    button.disabled = false;
                }
            } catch (error) {
                console.error('Error al inscribirse en el torneo individual:', error);
                showFlashMessage('Error de red o inesperado al inscribirse.', 'error');
                button.textContent = 'Inscribirse';
                button.disabled = false;
            }
        }
    }

    // --- FUNCIONES PARA EL MODAL DE INSCRIPCIÓN A DOBLES (MOVIDAS DESDE PLAYER_DASHBOARD.JS Y ADAPTADAS) ---

    async function openDoublesEnrollmentModal(tournament) {
        if (doublesEnrollmentModal) {
            modalTournamentNameSpan.textContent = tournament.name;
            modalTournamentIdInput.value = tournament.id;
            modalTournamentTypeInput.value = tournament.type;
            
            doublesEnrollmentMessageDiv.textContent = ''; // Limpiar mensajes del modal
            partnerSearchInputModal.value = '';
            partnerSearchResultsModalDiv.innerHTML = '<p>Los resultados de tu búsqueda aparecerán aquí.</p>';


            // Cargar equipos existentes del jugador para el select
            let gender_category_filter = '';
            if (tournament.type.includes('male')) {
                gender_category_filter = 'Masculino';
            } else if (tournament.type.includes('female')) {
                gender_category_filter = 'Femenino';
            } else if (tournament.type.includes('mixed')) {
                gender_category_filter = 'Mixto'; // Si tienes categoría mixta en Teams.gender_category
            }
            await loadExistingTeamsForPlayer(gender_category_filter); // Cargar equipos que coincidan con el género del torneo

            doublesEnrollmentModal.style.display = 'flex';
        }
    }

    function closeDoublesEnrollmentModal() {
        if (doublesEnrollmentModal) {
            doublesEnrollmentModal.style.display = 'none';
        }
    }

    // Función para cargar equipos globales existentes del jugador logueado (desde /api/doubles/my_global_teams)
    async function loadExistingTeamsForPlayer(genderCategoryFilter) {
        if (existingTeamSelect) existingTeamSelect.innerHTML = '<option value="">Cargando equipos...</option>';

        try {
            // Este endpoint devuelve los equipos globales del jugador logueado
            // Asegúrate de que este endpoint exista y funcione en app.py
            const response = await fetch(`/api/doubles/my_global_teams?gender_category=${genderCategoryFilter}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error al cargar tus equipos existentes.');
            }
            const teams = await response.json();

            if (existingTeamSelect) {
                existingTeamSelect.innerHTML = '<option value="">Selecciona tu Equipo</option>';
                teams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = team.id;
                    option.textContent = `${team.team_name} (${team.player1_name} / ${team.player2_name})`;
                    existingTeamSelect.appendChild(option);
                });
                if (teams.length === 0) {
                    existingTeamSelect.innerHTML = '<option value="">No tienes equipos disponibles para este tipo de torneo.</option>';
                    existingTeamSelect.disabled = true;
                    if (enrollWithExistingTeamBtn) enrollWithExistingTeamBtn.disabled = true;
                } else {
                    existingTeamSelect.disabled = false;
                    if (enrollWithExistingTeamBtn) enrollWithExistingTeamBtn.disabled = false;
                }
            }

        } catch (error) {
            console.error('Error en loadExistingTeamsForPlayer:', error);
            if (existingTeamSelect) existingTeamSelect.innerHTML = '<option value="">Error al cargar equipos.</option>';
            if (enrollWithExistingTeamBtn) enrollWithExistingTeamBtn.disabled = true;
        }
    }

    // FUNCIÓN: Buscar jugadores elegibles para ser compañeros para ESTE torneo
    async function searchPartnersForTournament() {
        const searchTerm = partnerSearchInputModal.value.trim();
        const currentTournamentId = modalTournamentIdInput.value;
        const currentTournamentType = modalTournamentTypeInput.value; // Obtener el tipo de torneo de dobles

        if (!searchTerm) {
            showFlashMessage('Por favor, escribe un nombre o apellido para buscar.', 'info');
            partnerSearchResultsModalDiv.innerHTML = '';
            return;
        }
        if (!currentTournamentId || !currentTournamentType) {
            showFlashMessage('Error interno: Información del torneo no disponible para búsqueda.', 'error');
            return;
        }

        if (partnerSearchResultsModalDiv) partnerSearchResultsModalDiv.innerHTML = '<p>Buscando jugadores...</p>';

        try {
            // Pasar el tournament_id y el tipo de torneo (para género) al backend
            const response = await fetch(`/api/players/search_partners?q=${encodeURIComponent(searchTerm)}&tournament_id=${currentTournamentId}&tournament_gender_type=${currentTournamentType}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error al buscar compañeros.');
            }
            const players = await response.json();

            if (partnerSearchResultsModalDiv) partnerSearchResultsModalDiv.innerHTML = '';

            if (players.length === 0) {
                if (partnerSearchResultsModalDiv) partnerSearchResultsModalDiv.innerHTML = '<p>No se encontraron jugadores elegibles.</p>';
                return;
            }

            const ul = document.createElement('ul');
            ul.className = 'partner-results-list';
            players.forEach(player => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span>${player.first_name} ${player.last_name} (Puesto: ${player.current_position}, Género: ${player.gender})</span>
                    <button class="button small-button request-partner-btn" data-player-id="${player.id}"
                            data-player-name="${player.first_name} ${player.last_name}"
                            data-tournament-id="${currentTournamentId}" style="margin-left: 10px;">
                        Solicitar
                    </button>
                `;
                ul.appendChild(li);
            });
            if (partnerSearchResultsModalDiv) partnerSearchResultsModalDiv.appendChild(ul);

            // Añadir event listeners a los nuevos botones "Solicitar"
            document.querySelectorAll('#partner-search-results-modal .request-partner-btn').forEach(button => {
                button.addEventListener('click', (event) => {
                    const tournamentId = event.target.dataset.tournamentId; // Obtener de data-attribute
                    requestPartnerForTournament(event, parseInt(tournamentId));
                });
            });

        } catch (error) {
            console.error('Error en searchPartnersForTournament:', error);
            if (partnerSearchResultsModalDiv) partnerSearchResultsModalDiv.innerHTML = `<p class="error-message">Error al buscar compañeros: ${error.message}</p>`;
        }
    }

    // Función para enviar solicitud de compañero para un torneo
    async function requestPartnerForTournament(event, tournamentId) {
        const button = event.target;
        const requestedPlayerId = button.dataset.playerId;
        const requestedPlayerName = button.dataset.playerName;

        if (!confirm(`¿Estás seguro de que quieres enviar una solicitud de compañero a ${requestedPlayerName} para este torneo?`)) {
            return;
        }

        button.disabled = true;
        button.textContent = 'Enviando...';

        try {
            const response = await fetch('/api/doubles/request_partner_v2', { // Endpoint de solicitud de compañero
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    requested_player_id: parseInt(requestedPlayerId),
                    tournament_id: parseInt(tournamentId) // Enviar el ID del torneo
                })
            });

            const result = await response.json();

            if (response.ok) {
                showFlashMessage(result.message, 'success');
                button.textContent = 'Solicitud Enviada';
                // Recargar la lista de torneos para actualizar estado del botón
                loadTournaments(); // En tournaments.js, loadTournaments recarga los botones de inscripción
                closeDoublesEnrollmentModal(); // Cerrar el modal después de enviar la solicitud
            } else {
                showFlashMessage(result.error || 'Error al enviar solicitud.', 'error');
                button.textContent = 'Solicitar';
                button.disabled = false;
            }
        } catch (error) {
            console.error('Error al enviar solicitud de compañero:', error);
            showFlashMessage('Error de red o inesperado al enviar solicitud.', 'error');
            button.textContent = 'Solicitar';
            button.disabled = false;
        }
    }


    // Función para inscribir un equipo existente a un torneo
    async function enrollWithExistingTeam() {
        const selectedTeamId = existingTeamSelect ? existingTeamSelect.value : null;
        const tournamentId = modalTournamentIdInput ? parseInt(modalTournamentIdInput.value) : null;
        const tournamentName = modalTournamentNameSpan ? modalTournamentNameSpan.textContent : 'este torneo';

        if (!selectedTeamId) {
            showFlashMessage('Por favor, selecciona un equipo existente.', 'error');
            return;
        }
        if (!tournamentId) {
            showFlashMessage('Error: ID del torneo no encontrado.', 'error');
            return;
        }

        if (!confirm(`¿Estás seguro de inscribir a tu equipo seleccionado en "${tournamentName}"?`)) {
            return;
        }

        if (enrollWithExistingTeamBtn) {
            enrollWithExistingTeamBtn.disabled = true;
            enrollWithExistingTeamBtn.textContent = 'Inscribiendo...';
        }

        try {
            // Nuevo endpoint para inscribir un equipo existente a un torneo
            // Este endpoint debe registrar el team_id y tournament_id en TournamentRegistrations
            // Y posiblemente en TournamentTeams si el torneo es pirámide.
            const response = await fetch('/api/doubles/enroll_existing_team', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ team_id: parseInt(selectedTeamId), tournament_id: tournamentId })
            });

            const result = await response.json();

            if (response.ok) {
                showFlashMessage(result.message, 'success');
                closeDoublesEnrollmentModal();
                loadTournaments(); // Recargar la lista de torneos para reflejar la inscripción
            } else {
                showFlashMessage(result.error || 'Error al inscribir equipo.', 'error');
                if (enrollWithExistingTeamBtn) {
                    enrollWithExistingTeamBtn.textContent = 'Inscribir Equipo';
                    enrollWithExistingTeamBtn.disabled = false;
                }
            }
        } catch (error) {
            console.error('Error al inscribir equipo existente:', error);
            showFlashMessage('Error de red o inesperado al inscribir equipo.', 'error');
            if (enrollWithExistingTeamBtn) {
                enrollWithExistingTeamBtn.textContent = 'Inscribir Equipo';
                enrollWithExistingTeamBtn.disabled = false;
            }
        }
    }


    // --- Inicialización de Event Listeners y Cargas al cargar el DOM ---
    // Listeners para filtros
    applyFiltersBtn.addEventListener('click', loadTournaments);

    // Listeners para el modal de dobles
    if (searchPartnersModalBtn) {
        searchPartnersModalBtn.addEventListener('click', searchPartnersForTournament);
    }
    if (partnerSearchInputModal) { // Permitir buscar al presionar Enter
        partnerSearchInputModal.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                searchPartnersForTournament();
            }
        });
    }
    if (enrollWithExistingTeamBtn) {
        enrollWithExistingTeamBtn.addEventListener('click', enrollWithExistingTeam);
    }
    if (closeDoublesEnrollmentModalBtn) {
        closeDoublesEnrollmentModalBtn.addEventListener('click', closeDoublesEnrollmentModal);
    }

    // Cargar torneos al iniciar la página
    loadTournaments();
});