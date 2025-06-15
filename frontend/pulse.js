import { config } from './pulse-config.js';

// pulse_shrine_app.js

let runes = [];

// Initialiser l'hôtel à runes
function initRuneHotel() {
    const nbRunes = 8;
    const hotel = document.getElementById('runeHotel');
    for (let i = 0; i < nbRunes; i++) {
        const slot = document.createElement('div');
        slot.className = 'rune-slot';
        slot.id = `rune-slot-${i}`;
        hotel.appendChild(slot);
    }
}

// Créer une rune
function createRune(intention, feeling) {
    const runeSymbols = ['☯', '✧', '◈', '※', '⟡', '◊', '⬟', '◈', '✦', '⟢', '◇', '※', '◉', '⬢', '◈', '⟡'];
    const symbol = runeSymbols[Math.floor(Math.random() * runeSymbols.length)];
    const rune = {
        symbol: symbol,
        intention: intention,
        feeling: feeling,
        name: generateRuneName(intention, feeling)
    };
    runes.push(rune);
    addRuneToHotel(rune);
    return rune;
}

// Générer un nom de rune
function generateRuneName(intention, feeling) {
    const prefixes = ['Lum', 'Ser', 'Zen', 'Har', 'Paz', 'Aur', 'Vel', 'Lyr'];
    const suffixes = ['nis', 'ara', 'eth', 'ion', 'ora', 'ium', 'ael', 'ys'];
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
    const suffix = suffixes[Math.floor(Math.random() * suffixes.length)];
    return prefix + suffix;
}

// Ajouter une rune à l'hôtel
function addRuneToHotel(rune) {
    const emptySlots = document.querySelectorAll('.rune-slot:not(.filled)');
    if (emptySlots.length > 0) {
        const slot = emptySlots[0];
        slot.className = 'rune-slot filled';
        slot.innerHTML = `<span class="rune-symbol">${rune.symbol}</span>`;
        slot.title = `${rune.name} - ${rune.intention}`;
    }
}

// Gestion des phases
function showMessage(message) {
    const sageMessage = document.getElementById('sageMessage');
    sageMessage.textContent = message;
    sageMessage.classList.add('fade-in');
}

function showElement(elementId) {
    document.getElementById(elementId).classList.remove('hidden');
}

function hideElement(elementId) {
    document.getElementById(elementId).classList.add('hidden');
}

async function callPulseAPI(apiEndpoint, requestBody) {
    if (!config.apiKey || !config.apiBaseUrl) {
        throw new Error('API configuration is missing. Please config.');
    }
    try {
        const response = await fetch(`${config.apiBaseUrl}${apiEndpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': config.apiKey
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        console.log('Success:', data);
        return data;
    } catch (error) {
        console.error('Error:', error);
        throw error; // Re-throw the error to handle it in the calling function if needed
    }
}

async function callStartPulseAPI(user_id, intention) {
    await callPulseAPI('/start-pulse', { user_id: user_id, intent: intention });
}

async function callStopPulseAPI(user_id, reflection) {
    await callPulseAPI('/stop-pulse', { user_id: user_id, reflection: reflection });
}

// Initialisation après chargement du DOM
document.addEventListener('DOMContentLoaded', function () {
    initRuneHotel();

    // Phase 1: Démarrer un pulse
    document.getElementById('startPulseBtn').addEventListener('click', function () {
        showMessage("Ah, je sens votre énergie s'éveiller... L'autel résonne : indiquez-lui votre intention.");
        hideElement('pulseControls');
        showElement('intentionPhase');
    });

    // Phase 2: Valider l'intention
    document.getElementById('validateIntentionBtn').addEventListener('click', async function () {
        const intention = document.getElementById('intentionInput').value.trim();
        if (intention) {
            showMessage("Votre intention s'élève vers les cieux... Le pulse commence à résonner dans tout le sanctuaire.");

            // START the animation BEFORE the blocking call
            const shrineElement = document.querySelector('.shrine'); // or whatever your shrine element is
            shrineElement.classList.add('shrine-glow');

            showMessage("Votre intention s'élève vers les cieux... Le pulse commence à résonner dans tout le sanctuaire.");
            hideElement('intentionPhase');

            try {
                await callStartPulseAPI("jerome", intention);
            } catch (error) {
                // Handle any errors from the API call
                showMessage("Une erreur s'est produite lors de l'envoi de votre intention. Veuillez réessayer.");
                shrineElement.classList.remove('shrine-glow');
                return;
            }
            //shrineElement.classList.remove('shrine-glow');
            showElement('pulseActive');
        }
    });

    // Phase 3: Arrêter le pulse
    document.getElementById('stopPulseBtn').addEventListener('click', async function () {
        showMessage("Le pulse s'apaise doucement... Partagez-moi maintenant votre ressenti, noble âme. Comment cette expérience vous a-t-elle transformé ?");
        hideElement('pulseActive');
        showElement('reflectionPhase');
    });

    // Phase 4: Finaliser et créer la rune
    document.getElementById('validateFeelingBtn').addEventListener('click', async function () {
        const intention = document.getElementById('intentionInput').value.trim();
        const feeling = document.getElementById('feelingInput').value.trim();
               const shrineElement = document.querySelector('.shrine'); // or whatever your shrine element is
        shrineElement.classList.remove('shrine-glow');

        try {
            await callStopPulseAPI("jerome", intention);
        } catch (error) {
            // Handle any errors from the API call
            showMessage("Une erreur s'est produite lors de l'envoi de votre reflexion. Veuillez réessayer.");
            return;
        }
        if (feeling) {
            const rune = createRune(intention, feeling);
            showMessage(`Merveilleux... Votre énergie s'est cristallisée en une rune sacrée : "${rune.name}". Elle rejoindra l'hôtel de notre sanctuaire et continuera de rayonner votre intention. Vous pouvez maintenant commencer un nouveau pulse quand vous le souhaiterez.`);
            hideElement('reflectionPhase');
            showElement('pulseControls');
            document.getElementById('intentionInput').value = '';
            document.getElementById('feelingInput').value = '';
        }
    });
});
