// static/all_matches.js

document.addEventListener('DOMContentLoaded', () => {
    loadAllMatches();
});

async function loadAllMatches() {
    const allMatchesListDiv = document.getElementById('all-matches-list');
    const allMatchesTableBody = document.querySelector('#all-matches-table tbody');
    const doublesGenderFilter = document.getElementById('doubles-gender-filter'); // El nuevo selector de género

    if (!allMatchesListDiv || !allMatchesTableBody || !doublesGenderFilter) {
        console.warn("Elementos requeridos del DOM no encontrados.");
        return;
    }

    allMatchesTableBody.innerHTML = ''; // Limpiar cualquier contenido previo en el tbody
    // Reajustar el thead para que siempre tenga las columnas correctas y no se dupliquen
    const tableHeadersRow = document.querySelector('#all-matches-table thead tr');
    tableHeadersRow.innerHTML = `
        <th>Fecha</th>
        <th>Desafiante</th>
        <th>Desafiado</th>
        <th>Ganador</th>
        <th>Perdedor</th>
        <th>Marcador</th>
        <th>Tipo</th>
        <th>Torneo</th>
    `;
    
    const loadingMessageP = allMatchesListDiv.querySelector('p');
    loadingMessageP.textContent = 'Cargando todos los partidos...';
    loadingMessageP.style.display = 'block';
    loadingMessageP.style.color = 'black'; // Resetear color de error

    let allMatches = [];

    try {
        // --- Cargar partidos individuales (Siempre se cargan) ---
        const responseSingle = await fetch('/api/all_matches');
        if (!responseSingle.ok) {
            const errorData = await responseSingle.json(); // Intentar leer el mensaje de error del backend
            throw new Error(`Error al cargar partidos individuales: ${errorData.message || responseSingle.statusText}`);
        }
        const singleMatches = await responseSingle.json();
        console.log("Todos los partidos individuales obtenidos:", singleMatches);

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
                type: 'Individual',
                tournament_name: match.tournament_name // NUEVO: Obtener nombre del torneo
            });
        });

        // --- Cargar partidos de dobles (Condicional al filtro) ---
        const selectedGender = doublesGenderFilter.value;
        if (selectedGender === '' || selectedGender === 'Masculino' || selectedGender === 'Femenino') {
            let doublesApiUrl = '/api/all_doubles_matches';
            if (selectedGender === 'Masculino') {
                doublesApiUrl += '?gender=Masculino';
            } else if (selectedGender === 'Femenino') {
                doublesApiUrl += '?gender=Femenino';
            }

            const responseDoubles = await fetch(doublesApiUrl);
            
            if (!responseDoubles.ok) {
                // Si es un 404 con mensaje específico, lo manejamos como informativo y no como error fatal
                if (responseDoubles.status === 404) {
                    const errorData = await responseDoubles.json();
                    console.warn(`Advertencia al cargar dobles: ${errorData.message}`);
                    // Podríamos mostrar este mensaje en algún lugar de la UI si no hay partidos de dobles
                } else {
                    const errorData = await responseDoubles.json();
                    throw new Error(`Error al cargar partidos de dobles: ${errorData.message || responseDoubles.statusText}`);
                }
            } else {
                const doublesMatches = await responseDoubles.json();
                console.log("Todos los partidos de dobles obtenidos:", doublesMatches);

                // Formatear partidos de dobles
                doublesMatches.forEach(match => {
                    allMatches.push({
                        id: match.id,
                        date: match.date,
                        challenger_name: match.challenger_name,
                        challenged_name: match.challenged_name,
                        winner_name: match.winner_name,
                        loser_name: match.loser_name,
                        score_text: match.score_text,
                        type: 'Dobles',
                        tournament_name: match.tournament_name // NUEVO: Obtener nombre del torneo
                    });
                });
            }
        }


        // Ordenar todos los partidos por fecha de forma descendente
        allMatches.sort((a, b) => new Date(b.date) - new Date(a.date));

        loadingMessageP.style.display = 'none'; // Ocultar mensaje de carga

        if (allMatches.length === 0) {
            loadingMessageP.textContent = 'No hay partidos registrados aún para la selección actual.';
            loadingMessageP.style.display = 'block';
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

            const typeCell = row.insertCell();
            typeCell.textContent = match.type;

            const tournamentCell = row.insertCell(); // NUEVA CELDA PARA EL NOMBRE DEL TORNEO
            tournamentCell.textContent = match.tournament_name || 'N/A';
        });

    } catch (error) {
        console.error('ERROR en loadAllMatches:', error);
        loadingMessageP.textContent = `Error al cargar los partidos: ${error.message}`;
        loadingMessageP.style.color = 'red';
        loadingMessageP.style.display = 'block';
    }
}