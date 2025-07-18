// static/register.js

document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('register-form');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const flashMessagesContainer = document.querySelector('.flash-messages'); // Contenedor para mensajes flash

    // Función para mostrar mensajes de error/éxito en el frontend (similar a flash messages)
    function showFrontendMessage(message, type) {
        // Limpiar mensajes anteriores si los hay
        if (flashMessagesContainer) {
            flashMessagesContainer.innerHTML = '';
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `flash-message ${type}`;
        messageDiv.textContent = message;
        if (flashMessagesContainer) {
            flashMessagesContainer.appendChild(messageDiv);
        } else {
            // Fallback si no se encuentra el contenedor, mostrar como alerta
            alert(message);
        }
    }

    if (registerForm) {
        registerForm.addEventListener('submit', function(event) {
            // Limpiar mensajes anteriores al intentar enviar
            if (flashMessagesContainer) {
                flashMessagesContainer.innerHTML = '';
            }

            // Validación del lado del cliente
            let isValid = true;
            let errorMessage = '';

            if (usernameInput.value.trim() === '') {
                errorMessage += 'El nombre de usuario es requerido.\n';
                isValid = false;
            }
            if (emailInput.value.trim() === '') {
                errorMessage += 'El email es requerido.\n';
                isValid = false;
            } else if (!/\S+@\S+\.\S+/.test(emailInput.value)) {
                errorMessage += 'El email no tiene un formato válido.\n';
                isValid = false;
            }
            if (passwordInput.value === '') {
                errorMessage += 'La contraseña es requerida.\n';
                isValid = false;
            }
            if (confirmPasswordInput.value === '') {
                errorMessage += 'La confirmación de contraseña es requerida.\n';
                isValid = false;
            }
            if (passwordInput.value !== confirmPasswordInput.value) {
                errorMessage += 'Las contraseñas no coinciden.\n';
                isValid = false;
            }

            if (!isValid) {
                event.preventDefault(); // Detener el envío del formulario
                showFrontendMessage(errorMessage, 'error');
                return;
            }

            // Si todo es válido, el formulario se enviará normalmente al backend.
            // No necesitamos un fetch aquí porque el formulario ya tiene action y method.
            // El backend manejará la inserción y la redirección.
        });
    }
});