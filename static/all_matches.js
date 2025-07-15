// static/all_matches.js

document.addEventListener('DOMContentLoaded', () => {
    loadAllMatches();
});

async function loadAllMatches() {
    const allMatchesListDiv = document.getElementById('all-matches-list');
    const allMatchesTableBody = document.querySelector('#all-matches-table tbody');

    if (!allMatchesListDiv || !allMatchesTableBody) {
        console.warn("Elementos 'all-matches-list' o 'all-matches-table tbody' no encontrados en el DOM.");
        return;
    }

    allMatchesTableBody.innerHTML = ''; // Limpiar cualquier contenido previo
    allMatchesListDiv.querySelector('p').textContent = 'Cargando todos los partidos...'; // Mostrar mensaje de carga

    try {
        // Obtener todos los partidos individuales
        const responseSingle = await fetch('/api/all_matches');
        if (!responseSingle.ok) {
            throw new Error(`Error al cargar partidos individuales: ${responseSingle.statusText}`);
        }
        const singleMatches = await responseSingle.json();
        console.log("Todos los partidos individuales obtenidos:", singleMatches);

        // Obtener todos los partidos de dobles
        const responseDoubles = await fetch('/api/all_doubles_matches'); // Llama al nuevo endpoint
        if (!responseDoubles.ok) {
            throw new Error(`Error al cargar partidos de dobles: ${responseDoubles.statusText}`);
        }
        const doublesMatches = await responseDoubles.json();
        console.log("Todos los partidos de dobles obtenidos:", doublesMatches);

        let allMatches = [];

        // Formatear partidos individuales
        singleMatches.forEach(match => {
            allMatches.push({
                id: match.id,
                date: match.date,
                challenger_name: match.challenger_name,
                challenged_name: match.challenged_name,
                winner_name: match.winner_name,
                loser_name: match.loser_name,
                score_text: match.score_text,
                type: 'Individual'
            });
        });

        // Formatear partidos de dobles
        doublesMatches.forEach(match => {
            allMatches.push({
                id: match.id,
                date: match.date,
                challenger_name: match.challenger_name, // Ya viene como team_a_name
                challenged_name: match.challenged_name, // Ya viene como team_b_name
                winner_name: match.winner_name, // Ya viene como winner_team_name
                loser_name: match.loser_name,   // Ya viene como loser_team_name
                score_text: match.score_text,
                type: 'Dobles'
            });
        });

        // Ordenar todos los partidos por fecha de forma descendente
        allMatches.sort((a, b) => new Date(b.date) - new Date(a.date));

        allMatchesListDiv.querySelector('p').style.display = 'none'; // Ocultar mensaje de carga

        if (allMatches.length === 0) {
            allMatchesListDiv.querySelector('p').textContent = 'No hay partidos registrados aún.';
            allMatchesListDiv.querySelector('p').style.display = 'block';
            return;
        }

        allMatches.forEach(match => {
            const row = allMatchesTableBody.insertRow();
            
            const dateCell = row.insertCell();
            dateCell.textContent = new Date(match.date).toLocaleString('es-ES', { 
                year: 'numeric', 
                month: 'numeric', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit', 
                hour12: false 
            }); 

            const challengerCell = row.insertCell();
            challengerCell.textContent = match.challenger_name;

            const challengedCell = row.insertCell();
            challengedCell.textContent = match.challenged_name;

            const winnerCell = row.insertCell();
            winnerCell.textContent = match.winner_name;

            const loserCell = row.insertCell();
            loserCell.textContent = match.loser_name;

            const scoreCell = row.insertCell();
            scoreCell.textContent = match.score_text;

            const typeCell = row.insertCell(); // Nueva celda para el tipo de partido
            typeCell.textContent = match.type;
        });

        // Asegurarse de que el thead tenga la nueva columna 'Tipo'
        const tableHeaders = document.querySelector('#all-matches-table thead tr');
        if (!tableHeaders.querySelector('th:last-child').textContent.includes('Tipo')) {
            const th = document.createElement('th');
            th.textContent = 'Tipo';
            tableHeaders.appendChild(th);
        }

    } catch (error) {
        console.error('ERROR en loadAllMatches:', error);
        allMatchesListDiv.querySelector('p').textContent = `Error al cargar los partidos: ${error.message}`;
        allMatchesListDiv.querySelector('p').style.color = 'red';
        allMatchesListDiv.querySelector('p').style.display = 'block';
    }
}
