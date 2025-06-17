import { config } from './pulse-config.js';

// pulse.js

let runes = [];

// Initialize the rune altar
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

// Create a rune
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

// Generate a rune name
function generateRuneName(intention, feeling) {
    const prefixes = ['Lum', 'Ser', 'Zen', 'Har', 'Paz', 'Aur', 'Vel', 'Lyr'];
    const suffixes = ['nis', 'ara', 'eth', 'ion', 'ora', 'ium', 'ael', 'ys'];
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
    const suffix = suffixes[Math.floor(Math.random() * suffixes.length)];
    return prefix + suffix;
}

// Add a rune to the altar
function addRuneToHotel(rune) {
    const emptySlots = document.querySelectorAll('.rune-slot:not(.filled)');
    if (emptySlots.length > 0) {
        const slot = emptySlots[0];
        slot.className = 'rune-slot filled';
        slot.innerHTML = `<span class="rune-symbol">${rune.symbol}</span>`;
        slot.title = `${rune.name} - ${rune.intention}`;
    }
}

// Phase management
function showMessage(message) {
    const sageMessage = document.getElementById('sageMessage');
    sageMessage.textContent = message;
    sageMessage.classList.add('fade-in');
}

function showIntent(message) {
    const pulseIntent = document.getElementById('pulseIntent');
    pulseIntent.textContent = message;
    pulseIntent.classList.add('fade-in');
}


function showElement(elementId) {
    document.getElementById(elementId).classList.remove('hidden');
}

function hideElement(elementId) {
    document.getElementById(elementId).classList.add('hidden');
}

async function callPulseAPI(method, apiEndpoint, requestBody) {
    if (!config.apiKey || !config.apiBaseUrl) {
        throw new Error('API configuration is missing. Please config.');
    }
    try {
        const fetchOptions = {
            method,
            headers: {
            'Content-Type': 'application/json',
            'x-api-key': config.apiKey
            }
        };

        let url = `${config.apiBaseUrl}${apiEndpoint}`;

        if (method === 'GET' && requestBody && Object.keys(requestBody).length > 0) {
            // Append query params for GET
            const params = new URLSearchParams(requestBody).toString();
            url += `?${params}`;
        } else if (method !== 'GET') {
            fetchOptions.body = JSON.stringify(requestBody);
        }
        const response = await fetch(url, fetchOptions);

        if (!response.ok) {
            if (response.status == 429)
                throw new Error('API answered Too Many requests');
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

async function callGetStartPulseAPI(user_id) {
    return await callPulseAPI('GET', '/get-start-pulse', { user_id: user_id });

}

async function callGetStopPulsesAPI(user_id) {
    return await callPulseAPI('GET', '/get-stop-pulses', { user_id: user_id });
}

async function callGetIngestedPulsesAPI(user_id) {
    return await callPulseAPI('GET', '/get-ingested-pulses', { user_id: user_id });
}

async function callStartPulseAPI(user_id, intention) {
    return await callPulseAPI('POST', '/start-pulse', { user_id: user_id, intent: intention });
}

async function callStopPulseAPI(user_id, reflection) {
    return await callPulseAPI('POST', '/stop-pulse', { user_id: user_id, reflection: reflection });
}

// Initialization after DOM load
document.addEventListener('DOMContentLoaded', async function () {
    initRuneHotel();

    let currentPulse = await callGetStartPulseAPI("jerome") || undefined;
    console.log('GetStartPulse Result: ', currentPulse)
    let intention = currentPulse ? currentPulse.intent : undefined;
    console.log('Intention: ', intention)

    if (currentPulse) {
        console.log('Hiding Start Inpulse Controls as there is already a Pulse occuring.')
        hideElement('sageMessage');
        hideElement('pulseControls');
        showIntent(intention)
        showElement('pulseActive');
    }
    else {
        document.getElementById('intentionInput').value = '';
        document.getElementById('feelingInput').value = '';        
        showElement('sageMessage');
        showElement('pulseControls');        
        //showMessage("Your intention rises to the heavens... The pulse begins to resonate throughout the shrine.");
    }

    // Phase 1: Start a pulse
    document.getElementById('startPulseBtn').addEventListener('click', async function () {
        showMessage("Ah, I sense your energy awakening... The altar resonates: tell it your intention.");
        hideElement('pulseControls');
        hideElement('pulseActive');
        
        if (! currentPulse)
            showElement('intentionPhase');
    });

    // Phase 2: Validate intention
    document.getElementById('validateIntentionBtn').addEventListener('click', async function () {
        intention = document.getElementById('intentionInput').value.trim();

        if (intention) {
            showMessage("Your intention rises to the heavens... The pulse begins to resonate throughout the shrine.");

            // START the animation BEFORE the blocking call
            const shrineElement = document.querySelector('.shrine'); // or whatever your shrine element is
            shrineElement.classList.add('shrine-glow');

            showMessage("Your intention rises to the heavens... The pulse begins to resonate throughout the shrine.");
            hideElement('intentionPhase');

            try {
                currentPulse = await callStartPulseAPI("jerome", intention);
                console.log('StartPulse Result:', currentPulse);
                intention = currentPulse.intent || "Something went wrong when retrievieng intent :<"
                showElement('sageMessage')
            } catch (error) {
                // Handle any errors from the API call
                showMessage("An error occurred while sending your intention. Please try again.");
                shrineElement.classList.remove('shrine-glow');
                return;
            }
            //shrineElement.classList.remove('shrine-glow');
            showIntent(intention)
            showElement('pulseActive');
        }
    });

    // Phase 3: Stop the pulse
    document.getElementById('stopPulseBtn').addEventListener('click', async function () {
        showMessage("The pulse gently subsides... Now share with me your feeling, noble soul. How did this experience transform you?");
        hideElement('pulseActive');
        showElement('reflectionPhase');
    });

    // Phase 4: Finalize and create the rune
    document.getElementById('validateFeelingBtn').addEventListener('click', async function () {
        intention = intention || document.getElementById('intentionInput').value.trim();
        const feeling = document.getElementById('feelingInput').value.trim();
        const shrineElement = document.querySelector('.shrine'); // or whatever your shrine element is
        shrineElement.classList.remove('shrine-glow');

        try {
            await callStopPulseAPI("jerome", feeling);
            currentPulse = undefined;
            intention = undefined;
        } catch (error) {
            // Handle any errors from the API call
            showMessage("An error occurred while sending your reflection. Please try again.");
            return;
        }
        if (feeling) {
            const rune = createRune(intention, feeling);
            showMessage(`Wonderful... Your energy has crystallized into a sacred rune: "${rune.name}". It will join the altar of our shrine and continue to radiate your intention. You can now start a new pulse whenever you wish.`);
            hideElement('reflectionPhase');
            showElement('sageMessage');
            showElement('pulseControls');
            document.getElementById('intentionInput').value = '';
            document.getElementById('feelingInput').value = '';
        }
    });
});
