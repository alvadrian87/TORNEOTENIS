// static/player_dashboard.js - REESCRITURA COMPLETA

document.addEventListener('DOMContentLoaded', function() {
    // --- 1. Inicialización de Variables y Elementos del DOM ---
    const userId = document.body.dataset.userId; 
    let playerId = document.body.dataset.playerId; 

    console.log(`DEBUG JS INIT: Valor original de data-player-id (string): '${playerId}'`); // <<-- AÑADIDO DEBUG
    
    // Convertir playerId a null si es una cadena vacía, "None", o no es un número válido.
    // De lo contrario, lo parseamos a un entero.
    if (playerId === '' || playerId === 'None' || playerId === 'null' || isNaN(parseInt(playerId))) {
        playerId = null;
        console.log("DEBUG JS INIT: playerId después de la primera verificación (null):", playerId); // <<-- AÑADIDO DEBUG
    } else {
        playerId = parseInt(playerId); 
        console.log("DEBUG JS INIT: playerId después de parseInt (number):", playerId); // <<-- AÑADIDO DEBUG
    }

    // Elementos del dashboard principal (información y estadísticas)
    const playerEmailSpan = document.getElementById('player-email');
    const playerFullNameSpan = document.getElementById('player-full-name');
    const playerCurrentPositionSpan = document.getElementById('player-current-position');
    const playerActivitySingleSpan = document.getElementById('player-activity-single');
    const playerStatusSingleSpan = document.getElementById('player-status-single');
    const playerActivityDoublesSpan = document.getElementById('player-activity-doubles');
    const playerStatusDoublesSpan = document.getElementById('player-status-doubles');
    const playerStatusGeneralSpan = document.getElementById('player-status-general');
    const playerLastActivityUpdateSpan = document.getElementById('player-last-activity-update');
    const playerRejectionsCurrentCycleSpan = document.getElementById('player-rejections-current-cycle');
    const playerRejectionsTotalSpan = document.getElementById('player-rejections-total');
    const playerMatchesHistoryDiv = document.getElementById('player-matches-history');

    // Elementos de la sección de Gestión de Solicitudes de Compañero
    const sentRequestsListDiv = document.getElementById('sent-requests-list');
    const receivedRequestsListDiv = document.getElementById('received-requests-list');
    const doublesFlashMessagesDiv = document.getElementById('doubles-flash-messages'); 

    // Elementos del modal "Editar mi perfil"
    const editProfileModal = document.getElementById('edit-profile-modal');
    const closeEditProfileModalBtn = document.querySelector('#edit-profile-modal .close-button');
    const editProfileForm = document.getElementById('edit-profile-form');
    const editPhoneInput = document.getElementById('edit-phone');
    const editGenderSelect = document.getElementById('edit-gender');
    const editBirthDateInput = document.getElementById('edit-birth-date');
    const editLocationInput = document.getElementById('edit-location');
    const editDominantHandSelect = document.getElementById('edit-dominant-hand');
    const editBackhandTypeSelect = document.getElementById('edit-backhand-type');
    const editRacquetInput = document.getElementById('edit-racquet');
    const editProfileMessageDiv = document.getElementById('edit-profile-message');
    const editProfileBtn = document.querySelector('.player-info-section .button.small-button'); // Botón "Editar mi perfil" en el dashboard


    // --- 2. Funciones de Utilidad ---

    function showGeneralFlashMessage(message, category) {
        const flashDiv = document.querySelector('.flash-messages');
        if (flashDiv) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${category}`;
            alertDiv.textContent = message;
            flashDiv.innerHTML = '';
            flashDiv.appendChild(alertDiv);
            setTimeout(() => alertDiv.remove(), 5000);
        } else {
            console.warn("Elemento para mensajes flash generales no encontrado.");
        }
    }

    function showDoublesFlashMessage(message, category) {
        if (doublesFlashMessagesDiv) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${category}`;
            alertDiv.textContent = message;
            doublesFlashMessagesDiv.innerHTML = ''; 
            doublesFlashMessagesDiv.appendChild(alertDiv);
            setTimeout(() => alertDiv.remove(), 5000);
        } else {
            console.warn("Elemento para mensajes flash de dobles no encontrado.");
        }
    }

    // --- 3. Funciones para Cargar Datos del Jugador y Estadísticas ---

    async function loadPlayerData() {
        console.log(`DEBUG JS: loadPlayerData() para Player ID: ${playerId}`);
        try {
            const response = await fetch('/api/player_data/me');
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error al cargar datos de tu perfil.');
            }
            const playerData = await response.json();

            // Rellenar campos del dashboard
            if (playerEmailSpan) playerEmailSpan.textContent = playerData.email || 'N/A';
            if (playerFullNameSpan) playerFullNameSpan.textContent = playerData.full_name || 'N/A';
            if (playerCurrentPositionSpan) playerCurrentPositionSpan.textContent = playerData.current_position || 'N/A';
            
            // Actualizar estadísticas de actividad
            if (playerActivitySingleSpan) playerActivitySingleSpan.textContent = playerData.activity_index_single || 0;
            if (playerStatusSingleSpan) playerStatusSingleSpan.textContent = playerData.activity_status_single || 'rojo';
            if (playerActivityDoublesSpan) playerActivityDoublesSpan.textContent = playerData.activity_index_doubles || 0;
            if (playerStatusDoublesSpan) playerStatusDoublesSpan.textContent = playerData.activity_status_doubles || 'rojo';
            if (playerStatusGeneralSpan) playerStatusGeneralSpan.textContent = playerData.activity_status || 'rojo';
            if (playerLastActivityUpdateSpan) playerLastActivityUpdateSpan.textContent = playerData.last_activity_update_formatted || 'Nunca';
            if (playerRejectionsCurrentCycleSpan) playerRejectionsCurrentCycleSpan.textContent = playerData.rejections_current_cycle || 0;
            if (playerRejectionsTotalSpan) playerRejectionsTotalSpan.textContent = playerData.rejections_total || 0;

            // Cargar historial de partidos del jugador
            if (playerMatchesHistoryDiv) {
                loadPlayerMatchesHistory(playerId, playerMatchesHistoryDiv);
            }

            // Rellenar el MODAL de edición con los datos actuales
            if (editPhoneInput) editPhoneInput.value = playerData.phone || '';
            if (editGenderSelect) editGenderSelect.value = playerData.gender || '';
            if (editBirthDateInput) editBirthDateInput.value = playerData.birth_date || ''; // YYYY-MM-DD
            if (editLocationInput) editLocationInput.value = playerData.location || '';
            if (editDominantHandSelect) editDominantHandSelect.value = playerData.dominant_hand || '';
            if (editBackhandTypeSelect) editBackhandTypeSelect.value = playerData.backhand_type || '';
            if (editRacquetInput) editRacquetInput.value = playerData.racquet || '';

        } catch (error) {
            console.error('Error en loadPlayerData:', error);
            showGeneralFlashMessage(`Error al cargar tus datos de jugador: ${error.message}`, 'error');
        }
    }

    async function loadPlayerMatchesHistory(playerId, targetDiv) {
        targetDiv.innerHTML = '<p>Cargando historial de partidos...</p>';
        try {
            const response = await fetch(`/api/players/${playerId}/history`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error al cargar el historial.');
            }
            const matches = await response.json();

            targetDiv.innerHTML = '';
            if (matches.length === 0) {
                targetDiv.innerHTML = '<p>Aún no has jugado partidos.</p>';
                return;
            }

            const ul = document.createElement('ul');
            ul.className = 'matches-history-list';
            matches.forEach(match => {
                const li = document.createElement('li');
                li.innerHTML = `
                    ${new Date(match.date).toLocaleDateString()}:
                    <strong>${match.winner_name}</strong> ganó a ${match.loser_name} (<strong>${match.score_text}</strong>)
                    <br><small>Tipo: ${match.match_type === 'single' ? 'Individual' : 'Dobles'}</small>
                `;
                ul.appendChild(li);
            });
            targetDiv.appendChild(ul);

        } catch (error) {
            console.error('Error en loadPlayerMatchesHistory:', error);
            targetDiv.innerHTML = `<p class="error-message">Error al cargar historial: ${error.message}</p>`;
        }
    }

    // --- 4. Funciones para Manejar el Modal "Editar mi perfil" ---

    function openEditProfileModal() {
        if (editProfileModal) {
            editProfileModal.style.display = 'flex';
        }
    }

    function closeEditProfileModal() {
        if (editProfileModal) {
            editProfileModal.style.display = 'none';
            if (editProfileMessageDiv) editProfileMessageDiv.textContent = ''; // Limpiar mensaje
        }
    }

    async function submitEditedProfile() {
        if (!editProfileForm) return;

        const formData = new FormData(editProfileForm);
        const data = {};
        formData.forEach((value, key) => {
            data[key] = value;
        });

        if (editProfileMessageDiv) editProfileMessageDiv.textContent = 'Guardando...';
        
        try {
            const response = await fetch('/api/player_data/me/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            if (response.ok) {
                showGeneralFlashMessage(result.message, 'success');
                if (editProfileMessageDiv) {
                    editProfileMessageDiv.textContent = result.message;
                    editProfileMessageDiv.className = 'message success';
                }
                loadPlayerData(); // Recargar datos para ver cambios en el dashboard
                closeEditProfileModal();
            } else {
                showGeneralFlashMessage(result.error || 'Error al actualizar perfil.', 'error');
                if (editProfileMessageDiv) {
                    editProfileMessageDiv.textContent = result.error || 'Error al actualizar perfil.';
                    editProfileMessageDiv.className = 'message error';
                }
            }
        } catch (error) {
            console.error('Error de red al actualizar perfil:', error);
            showGeneralFlashMessage('Error de red o inesperado al actualizar perfil.', 'error');
            if (editProfileMessageDiv) {
                editProfileMessageDiv.textContent = 'Error de conexión.';
                editProfileMessageDiv.className = 'message error';
            }
        }
    }


    // --- 5. Funciones para Cargar y Responder Solicitudes de Compañero ---

    async function loadMyPartnerRequests() {
        if (!sentRequestsListDiv || !receivedRequestsListDiv) {
            console.warn("Elementos para solicitudes de compañero no encontrados.");
            return;
        }

        sentRequestsListDiv.innerHTML = '<p>Cargando solicitudes enviadas...</p>';
        receivedRequestsListDiv.innerHTML = '<p>Cargando solicitudes recibidas...</p>';

        try {
            const response = await fetch('/api/doubles/my_partner_requests'); // Asegúrate de que esta URL sea correcta en tu app.py
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error al cargar tus solicitudes de compañero.');
            }
            const data = await response.json();
            const sentRequests = data.sent_requests;
            const receivedRequests = data.received_requests;

            // Renderizar solicitudes enviadas
            sentRequestsListDiv.innerHTML = '';
            if (sentRequests.length === 0) {
                sentRequestsListDiv.innerHTML = '<p>No has enviado ninguna solicitud de compañero.</p>';
            } else {
                sentRequests.forEach(request => {
                    const requestItem = document.createElement('div');
                    requestItem.className = 'request-item';
                    requestItem.innerHTML = `
                        <p>Solicitud a <strong>${request.requested_player_name}</strong> para el torneo <strong>${request.tournament_name}</strong>.</p>
                        <div class="request-actions">
                            <span class="request-status status-${request.status}">${request.status.charAt(0).toUpperCase() + request.status.slice(1)}</span>
                            ${request.status === 'pending' ? `<button class="cancel-btn" data-request-id="${request.id}">Cancelar</button>` : ''}
                        </div>
                    `;
                    sentRequestsListDiv.appendChild(requestItem);
                });
                // Attach listeners for newly created buttons
                sentRequestsListDiv.querySelectorAll('.cancel-btn').forEach(button => {
                    button.addEventListener('click', (event) => respondPartnerRequest(event.target.dataset.requestId, 'cancelled'));
                });
            }

            // Renderizar solicitudes recibidas
            receivedRequestsListDiv.innerHTML = '';
            if (receivedRequests.length === 0) {
                receivedRequestsListDiv.innerHTML = '<p>No has recibido ninguna solicitud de compañero.</p>';
            } else {
                receivedRequests.forEach(request => {
                    const requestItem = document.createElement('div');
                    requestItem.className = 'request-item';
                    requestItem.innerHTML = `
                        <p>Solicitud de <strong>${request.requester_player_name}</strong> para el torneo <strong>${request.tournament_name}</strong>.</p>
                        <div class="request-actions">
                            ${request.status === 'pending' ? `
                                <button class="accept-btn" data-request-id="${request.id}">Aceptar</button>
                                <button class="reject-btn" data-request-id="${request.id}">Rechazar</button>
                            ` : `<span class="request-status status-${request.status}">${request.status.charAt(0).toUpperCase() + request.status.slice(1)}</span>`}
                        </div>
                    `;
                    receivedRequestsListDiv.appendChild(requestItem);
                });

                // Attach listeners for newly created buttons
                receivedRequestsListDiv.querySelectorAll('.accept-btn').forEach(button => {
                    button.addEventListener('click', (event) => respondPartnerRequest(parseInt(event.target.dataset.requestId), 'accept')); // action 'accept'
                });
                receivedRequestsListDiv.querySelectorAll('.reject-btn').forEach(button => {
                    button.addEventListener('click', (event) => respondPartnerRequest(parseInt(event.target.dataset.requestId), 'reject')); // action 'reject'
                });
            }

        } catch (error) {
            console.error('Error en loadMyPartnerRequests:', error);
            showDoublesFlashMessage(`Error al cargar tus solicitudes: ${error.message}`, 'error');
            if (sentRequestsListDiv) sentRequestsListDiv.innerHTML = `<p class="error-message">Error al cargar solicitudes enviadas: ${error.message}</p>`;
            if (receivedRequestsListDiv) receivedRequestsListDiv.innerHTML = `<p class="error-message">Error al cargar solicitudes recibidas: ${error.message}</p>`;
        }
    }

    async function respondPartnerRequest(requestId, action) {
        try {
            const response = await fetch(`/api/doubles/respond_partner_request/${requestId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action: action })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || `Error al ${action} la solicitud.`);
            }

            showDoublesFlashMessage(data.message, 'success');
            loadMyPartnerRequests(); // Recargar las solicitudes para actualizar el estado

        } catch (error) {
            console.error(`Error al ${action} la solicitud:`, error);
            showDoublesFlashMessage(`Error: ${error.message}`, 'error');
        }
    }

    if (!playerId) { 
        console.warn('Usuario no vinculado a jugador (ID no válido), no se cargarán datos detallados del perfil ni funcionalidades de dobles.');
        console.log("DEBUG JS INIT: Script terminado debido a playerId no válido."); // <<-- AÑADIDO DEBUG
        return; 
    } else {
        console.log(`DEBUG: player_dashboard.js iniciado para Player ID: ${playerId}, User ID: ${userId}`);
    }


    // --- 6. Inicialización de Event Listeners y Cargas al cargar el DOM ---
    // Estas llamadas deben estar después de la verificación del player_id
    if (playerId) { // Solo si playerId es un número válido
        console.log("DEBUG JS: Intentando llamar a loadPlayerData() y loadMyPartnerRequests().");
        loadPlayerData();
        loadMyPartnerRequests(); // Cargar las solicitudes de compañero
        console.log("DEBUG JS: Llamadas a carga de datos iniciadas.");
    } else {
        console.warn('DEBUG JS: No hay Player ID válido. No se cargarán los datos del dashboard.');
    }

    // Listeners para el modal "Editar mi perfil"
    if (editProfileBtn) {
        editProfileBtn.addEventListener('click', openEditProfileModal);
    }
    if (closeEditProfileModalBtn) {
        closeEditProfileModalBtn.addEventListener('click', closeEditProfileModal);
    }
    if (editProfileForm) {
        editProfileForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Prevenir el envío por defecto del formulario
            submitEditedProfile();
        });
    }

}); // Cierre de DOMContentLoaded