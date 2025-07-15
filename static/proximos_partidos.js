// static/proximos_partidos.js

document.addEventListener('DOMContentLoaded', () => {
    loadUpcomingMatches();
});

async function loadUpcomingMatches() {
    const upcomingMatchesListDiv = document.getElementById('upcoming-matches-list');
    if (!upcomingMatchesListDiv) {
        console.warn("Elemento 'upcoming-matches-list' no encontrado en el DOM de proximos_partidos.html.");
        return;
    }

    upcomingMatchesListDiv.innerHTML = '<p>Cargando próximos partidos...</p>';

    try {
        // Obtener desafíos individuales pendientes
        const responseSingle = await fetch('/api/pending_challenges');
        if (!responseSingle.ok) {
            throw new Error(`Error al cargar desafíos individuales pendientes: ${responseSingle.statusText}`);
        }
        const singleChallenges = await responseSingle.json();
        console.log("Desafíos individuales pendientes obtenidos:", singleChallenges);

        // Obtener desafíos de dobles pendientes
        const responseDoubles = await fetch('/api/pending_doubles_challenges');
        if (!responseDoubles.ok) {
            throw new Error(`Error al cargar desafíos de dobles pendientes: ${responseDoubles.statusText}`);
        }
        const doublesChallenges = await responseDoubles.json();
        console.log("Desafíos de dobles pendientes obtenidos:", doublesChallenges);

        let allChallenges = [];

        // Formatear desafíos individuales
        singleChallenges.forEach(challenge => {
            allChallenges.push({
                id: challenge.id,
                date: challenge.created_at,
                challenger_name: challenge.challenger_name,
                challenged_name: challenge.challenged_name,
                type: 'Individual'
            });
        });

        // Formatear desafíos de dobles
        doublesChallenges.forEach(challenge => {
            allChallenges.push({
                id: challenge.id,
                date: challenge.created_at,
                challenger_name: challenge.challenger_team_name,
                challenged_name: challenge.challenged_team_name,
                type: 'Dobles'
            });
        });

        // Ordenar todos los desafíos por fecha de creación (más reciente primero)
        allChallenges.sort((a, b) => new Date(b.date) - new Date(a.date));

        upcomingMatchesListDiv.innerHTML = ''; // Limpiar el mensaje de carga

        if (allChallenges.length === 0) {
            upcomingMatchesListDiv.innerHTML = '<p>No hay partidos próximos o desafíos pendientes en este momento.</p>';
            return;
        }

        const ul = document.createElement('ul');
        ul.style.listStyle = 'none';
        ul.style.padding = '0';

        allChallenges.forEach(challenge => {
            const li = document.createElement('li');
            li.style.marginBottom = '10px';
            li.style.padding = '10px';
            li.style.border = '1px solid #007bff';
            li.style.borderRadius = '5px';
            li.style.backgroundColor = '#e7f0ff';
            li.innerHTML = `
                <p><strong>Fecha Propuesta:</strong> ${new Date(challenge.date).toLocaleDateString('es-ES', { 
                    year: 'numeric', month: 'numeric', day: 'numeric', 
                    hour: '2-digit', minute: '2-digit', hour12: false 
                })}</p>
                <p><strong>Tipo:</strong> ${challenge.type}</p>
                <p><strong>Desafío:</strong> ${challenge.challenger_name} vs ${challenge.challenged_name}</p>
                <hr>
            `;
            ul.appendChild(li);
        });
        upcomingMatchesListDiv.appendChild(ul);

    } catch (error) {
        console.error('ERROR en loadUpcomingMatches:', error);
        upcomingMatchesListDiv.innerHTML = `<p style="color: red;">Error al cargar próximos partidos: ${error.message}</p>`;
    }
}
