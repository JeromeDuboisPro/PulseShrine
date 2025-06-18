import { config } from './pulse-config.js';

// Constants
const NB_RUNES = 18;
const USER_ID = "jerome";
const RUNE_SYMBOLS = ['☯', '✧', '◈', '※', '⟡', '◊', '⬟', '◈', '✦', '⟢', '◇', '※', '◉', '⬢', '◈', '⟡'];
const RUNE_PREFIXES = ['Lum', 'Ser', 'Zen', 'Har', 'Paz', 'Aur', 'Vel', 'Lyr'];
const RUNE_SUFFIXES = ['nis', 'ara', 'eth', 'ion', 'ora', 'ium', 'ael', 'ys'];

let currentPulse = undefined;
let currentIntention = undefined;

let ingestedPulses = [];
let stoppedPulses = [];

// Periodically fetch ingested pulses
async function refreshPulses() {
    try {
        const now = new Date();
        console.log(`[${now.toLocaleString()}] Retrieving Stop & IngestedPulses`);
        const [ingested, stopped, started] = await Promise.all([
            PulseAPI.getIngestedPulses(USER_ID),
            PulseAPI.getStopPulses(USER_ID),
            PulseAPI.getStartPulse(USER_ID)
        ]);
        currentPulse = started;
        ingestedPulses = ingested.sort((a, b) => b.inverted_timestamp - a.inverted_timestamp);
        stoppedPulses = stopped;
        console.log("Retrieved StoppedPulses", currentPulse);
        console.log("Retrieved StoppedPulses", stoppedPulses);
        console.log("Retrieved IngestedPulses", ingestedPulses);
    } catch (e) {
        // Optionally handle error
    }
}

// Fill shrine with runes from ingestedPulses
async function fillShrineWithIngestedPulses() {
    await refreshPulses()
    const hotel = $('runeHotel');
    hotel.innerHTML = '';
    // Create a list of stopped pulses whose pulse_id is not in ingestedPulses
    const ingestedIdsSet = new Set(ingestedPulses.map(p => p.pulse_id));
    const curatedStoppedPulses = stoppedPulses.filter(p => !ingestedIdsSet.has(p.pulse_id));

    console.log("curatedStoppedPulses", curatedStoppedPulses);
    console.log("stoppedPulses", stoppedPulses);
    console.log("ingestedRunes", ingestedPulses);

    let limitedIngestedPulses = ingestedPulses;
    let limit = NB_RUNES - curatedStoppedPulses.length;
    let totalAmountOfPulses = curatedStoppedPulses.length + ingestedPulses.length;

    if (currentPulse) {
        limit = limit - 1;
        totalAmountOfPulses = totalAmountOfPulses + 1;
    }
    if (totalAmountOfPulses >= NB_RUNES) {
        limitedIngestedPulses = ingestedPulses.slice(-Math.max(0, limit));
    }

    // Display limitedIngestedPulses first
    let runeIndex = 0;
    for (; runeIndex < limitedIngestedPulses.length && runeIndex < NB_RUNES; runeIndex++) {
        const pulse = limitedIngestedPulses[runeIndex];
        const slot = document.createElement('div');
        slot.className = 'rune-slot filled';
        slot.id = `rune-slot-${runeIndex}`;
        const badge = pulse.gen_badge;
        const symbol = badge ? badge.trim().split(' ')[0] : randomFrom(RUNE_SYMBOLS);
        slot.innerHTML = `<span class="rune-symbol">${symbol}</span>`;
        slot.title = `${pulse.gen_title || 'Rune'} - ${pulse.intent || 'Intent went spiritual'} - ${pulse.reflection || 'Reflection is in progress'}`;
        hotel.appendChild(slot);
    }

    // Then display curatedStoppedPulses
    for (let j = 0; runeIndex < NB_RUNES && j < curatedStoppedPulses.length; j++, runeIndex++) {
        const pulse = curatedStoppedPulses[j];
        const slot = document.createElement('div');
        slot.className = 'rune-slot filled-stop';
        slot.id = `rune-slot-${runeIndex}`;
        const badge = '🟢';
        const symbol = badge ? badge.trim().split(' ')[0] : randomFrom(RUNE_SYMBOLS);
        slot.innerHTML = `<span class="rune-symbol">${symbol}</span>`;
        slot.title = `${pulse.gen_title || 'Rune'} - ${pulse.intent || 'Intent went spiritual'} - ${pulse.reflection || 'Reflection is in progress'}`;
        hotel.appendChild(slot);
    }

    if (currentPulse && runeIndex < NB_RUNES) {
        const slot = document.createElement('div');
        slot.className = 'rune-slot filled-start';
        slot.id = `rune-slot-${runeIndex}`;
        const badge = currentPulse.gen_badge || '⏳';
        const symbol = badge.trim().split(' ')[0];
        slot.innerHTML = `<span class="rune-symbol">${symbol}</span>`;
        slot.title = `${currentPulse.gen_title || 'Active Rune'} - ${currentPulse.intent || 'Intent in progress'} - Pulse is active`;
        hotel.appendChild(slot);
        runeIndex++;
    }

    // Fill remaining slots as empty
    for (; runeIndex < NB_RUNES; runeIndex++) {
        const slot = document.createElement('div');
        slot.className = 'rune-slot';
        slot.id = `rune-slot-${runeIndex}`;
        hotel.appendChild(slot);
    }
}


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
async function initRuneHotel() {
    await fillShrineWithIngestedPulses();
    return;
}

async function createRune(intention, feeling) {
    await fillShrineWithIngestedPulses();
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
    // Start periodic refresh
    setInterval(() => { fillShrineWithIngestedPulses(); }, 60 * 1000);

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
        showIntent(intention);
        showElement('pulseActive');
        showElement('sageMessage');
        try {
            currentPulse = await PulseAPI.startPulse(USER_ID, intention);
        } catch (e) {
            showMessage("An error occurred while sending your intention. Please try again.");
            setShrineGlow(false);
            return;
        }
        fillShrineWithIngestedPulses();
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
        currentPulse = undefined;
        currentIntention = undefined;
        if (feeling) {
            createRune(intention, feeling);
            showMessage(`Wonderful... Your energy will cristalize in a sacred rune soon. It will join the altar of our shrine and continue to radiate your intention. You can now start a new pulse whenever you wish.`);
            hideElement('reflectionPhase');
            showElement('sageMessage');
            showElement('pulseControls');
            resetInputs();
        }
        try {
            await PulseAPI.stopPulse(USER_ID, feeling);

        } catch (e) {
            showMessage("An error occurred while sending your reflection. Please try again.");
            return;
        }
        fillShrineWithIngestedPulses();
    });
});
