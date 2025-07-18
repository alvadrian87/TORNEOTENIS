// static/complete_player_profile.js

document.addEventListener('DOMContentLoaded', function() {
    const playerProfileForm = document.getElementById('player-profile-form');
    const flashMessagesContainer = document.querySelector('.flash-messages');

    // Función para mostrar mensajes de error/éxito en el frontend
    function showFrontendMessage(message, type) {
        if (flashMessagesContainer) {
            flashMessagesContainer.innerHTML = ''; // Limpiar mensajes anteriores
            const messageDiv = document.createElement('div');
            messageDiv.className = `flash-message ${type}`;
            messageDiv.textContent = message;
            flashMessagesContainer.appendChild(messageDiv);
        } else {
            alert(message); // Fallback si no se encuentra el contenedor
        }
    }

    if (playerProfileForm) {
        playerProfileForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Evitar el envío por defecto del formulario

            if (flashMessagesContainer) {
                flashMessagesContainer.innerHTML = ''; // Limpiar mensajes anteriores al intentar enviar
            }

            // --- Validación del lado del cliente ---
            let isValid = true;
            let errorMessage = '';

            const firstName = document.getElementById('first_name').value.trim();
            const lastName = document.getElementById('last_name').value.trim();
            const gender = document.getElementById('gender').value;
            const birthDate = document.getElementById('birth_date').value;
            // El email es readonly, asumimos que es correcto del session.email

            if (!firstName) {
                errorMessage += 'El nombre es requerido.\n';
                isValid = false;
            }
            if (!lastName) {
                errorMessage += 'El apellido es requerido.\n';
                isValid = false;
            }
            if (!gender) {
                errorMessage += 'El género es requerido.\n';
                isValid = false;
            }
            if (!birthDate) {
                errorMessage += 'La fecha de nacimiento es requerida.\n';
                isValid = false;
            }

            if (!isValid) {
                showFrontendMessage(errorMessage, 'error');
                return;
            }

            // --- Preparar datos para el envío (incluyendo archivo) ---
            const formData = new FormData(playerProfileForm); // FormData maneja automáticamente los campos y archivos

            try {
                const response = await fetch('/complete_player_profile', {
                    method: 'POST',
                    body: formData // No Content-Type header; FormData lo establece automáticamente
                });

                const data = await response.json();

                if (response.ok) {
                    showFrontendMessage(data.message, 'success');
                    alert(data.message); // Alerta adicional de confirmación
                    window.location.href = '/player_dashboard'; // Redirigir al dashboard después de guardar
                } else {
                    showFrontendMessage(data.error || 'Ocurrió un error desconocido al guardar el perfil.', 'error');
                    console.error('Error al guardar perfil de jugador:', data.error);
                }
            } catch (error) {
                console.error('ERROR de conexión al guardar el perfil de jugador:', error);
                showFrontendMessage('Error de conexión con el servidor al intentar guardar el perfil.', 'error');
            }
        });
    }
});