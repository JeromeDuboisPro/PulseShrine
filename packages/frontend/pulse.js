import { config } from './pulse-config.js';

// Constants
const NB_RUNES = 8;
const USER_ID = "jerome";
const RUNE_SYMBOLS = ['☯', '✧', '◈', '※', '⟡', '◊', '⬟', '◈', '✦', '⟢', '◇', '※', '◉', '⬢', '◈', '⟡'];
const RUNE_PREFIXES = ['Lum', 'Ser', 'Zen', 'Har', 'Paz', 'Aur', 'Vel', 'Lyr'];
const RUNE_SUFFIXES = ['nis', 'ara', 'eth', 'ion', 'ora', 'ium', 'ael', 'ys'];

let runes = [];
let currentPulse = undefined;
let currentIntention = undefined;

// --- UI Helpers ---
function $(id) {
    return document.getElementById(id);
}

function showElement(id) {
    $(id).classList.remove('hidden');
}

function hideElement(id) {
    $(id).classList.add('hidden');
}

function setText(id, text) {
    $(id).textContent = text;
}

function addClass(id, className) {
    $(id).classList.add(className);
}

function removeClass(id, className) {
    $(id).classList.remove(className);
}

// --- Rune Logic ---
function initRuneHotel() {
    const hotel = $('runeHotel');
    hotel.innerHTML = '';
    for (let i = 0; i < NB_RUNES; i++) {
        const slot = document.createElement('div');
        slot.className = 'rune-slot';
        slot.id = `rune-slot-${i}`;
        hotel.appendChild(slot);
    }
}

function createRune(intention, feeling) {
    const symbol = randomFrom(RUNE_SYMBOLS);
    const name = generateRuneName();
    const rune = { symbol, intention, feeling, name };
    runes.push(rune);
    addRuneToHotel(rune);
    return rune;
}

function generateRuneName() {
    return randomFrom(RUNE_PREFIXES) + randomFrom(RUNE_SUFFIXES);
}

function addRuneToHotel(rune) {
    const emptySlot = document.querySelector('.rune-slot:not(.filled)');
    if (emptySlot) {
        emptySlot.classList.add('filled');
        emptySlot.innerHTML = `<span class="rune-symbol">${rune.symbol}</span>`;
        emptySlot.title = `${rune.name} - ${rune.intention}`;
    }
}

function randomFrom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

// --- API Logic ---
async function callPulseAPI(method, endpoint, body) {
    if (!config.apiKey || !config.apiBaseUrl) {
        throw new Error('API configuration is missing.');
    }
    const url = new URL(config.apiBaseUrl + endpoint);
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': config.apiKey
        }
    };
    if (method === 'GET' && body && Object.keys(body).length) {
        Object.entries(body).forEach(([k, v]) => url.searchParams.append(k, v));
    } else if (method !== 'GET') {
        options.body = JSON.stringify(body);
    }
    const response = await fetch(url, options);
    if (!response.ok) {
        if (response.status === 429) throw new Error('Too Many Requests');
        throw new Error('Network response was not ok');
    }
    return response.json();
}

const PulseAPI = {
    getStartPulse: (userId) => callPulseAPI('GET', '/get-start-pulse', { user_id: userId }),
    getStopPulses: (userId) => callPulseAPI('GET', '/get-stop-pulses', { user_id: userId }),
    getIngestedPulses: (userId) => callPulseAPI('GET', '/get-ingested-pulses', { user_id: userId }),
    startPulse: (userId, intent) => callPulseAPI('POST', '/start-pulse', { user_id: userId, intent }),
    stopPulse: (userId, reflection) => callPulseAPI('POST', '/stop-pulse', { user_id: userId, reflection })
};

// --- UI Phase Logic ---
function showMessage(message) {
    setText('sageMessage', message);
    addClass('sageMessage', 'fade-in');
}

function showIntent(message) {
    setText('pulseIntent', message);
    addClass('pulseIntent', 'fade-in');
}

function resetInputs() {
    $('intentionInput').value = '';
    $('feelingInput').value = '';
}

function setShrineGlow(on) {
    const shrine = document.querySelector('.shrine');
    if (shrine) {
        shrine.classList.toggle('shrine-glow', on);
    }
}

// --- Main Flow ---
document.addEventListener('DOMContentLoaded', async () => {
    initRuneHotel();
    try {
        currentPulse = await PulseAPI.getStartPulse(USER_ID);
        currentIntention = currentPulse?.intent;
    } catch (e) {
        currentPulse = undefined;
        currentIntention = undefined;
    }

    if (currentPulse) {
        hideElement('sageMessage');
        hideElement('pulseControls');
        showIntent(currentIntention);
        showElement('pulseActive');
    } else {
        resetInputs();
        showElement('sageMessage');
        showElement('pulseControls');
    }

    // Start Pulse
    $('startPulseBtn').addEventListener('click', () => {
        showMessage("Ah, I sense your energy awakening... The altar resonates: tell it your intention.");
        hideElement('pulseControls');
        hideElement('pulseActive');
        if (!currentPulse) showElement('intentionPhase');
    });

    // Validate Intention
    $('validateIntentionBtn').addEventListener('click', async () => {
        const intention = $('intentionInput').value.trim();
        if (!intention) return;
        showMessage("Your intention rises to the heavens... The pulse begins to resonate throughout the shrine.");
        setShrineGlow(true);
        hideElement('intentionPhase');
        try {
            currentPulse = await PulseAPI.startPulse(USER_ID, intention);
            currentIntention = currentPulse.intent;
            showElement('sageMessage');
        } catch (e) {
            showMessage("An error occurred while sending your intention. Please try again.");
            setShrineGlow(false);
            return;
        }
        showIntent(currentIntention);
        showElement('pulseActive');
    });

    // Stop Pulse
    $('stopPulseBtn').addEventListener('click', () => {
        showMessage("The pulse gently subsides... Now share with me your feeling, noble soul. How did this experience transform you?");
        hideElement('pulseActive');
        showElement('reflectionPhase');
    });

    // Validate Feeling
    $('validateFeelingBtn').addEventListener('click', async () => {
        const intention = currentIntention || $('intentionInput').value.trim();
        const feeling = $('feelingInput').value.trim();
        setShrineGlow(false);
        try {
            await PulseAPI.stopPulse(USER_ID, feeling);
            currentPulse = undefined;
            currentIntention = undefined;
        } catch (e) {
            showMessage("An error occurred while sending your reflection. Please try again.");
            return;
        }
        if (feeling) {
            const rune = createRune(intention, feeling);
            showMessage(`Wonderful... Your energy has crystallized into a sacred rune: "${rune.name}". It will join the altar of our shrine and continue to radiate your intention. You can now start a new pulse whenever you wish.`);
            hideElement('reflectionPhase');
            showElement('sageMessage');
            showElement('pulseControls');
            resetInputs();
        }
    });
});
