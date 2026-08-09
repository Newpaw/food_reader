import {
  apiFetch,
  getCurrentUserContext,
  getJsonOrThrow,
  setupPage,
  showStatus,
} from './common.js?v=20260403-11';

let chatHistory = [];
let storageKey = null;
let isSending = false;

function isCzech() {
  return (document.documentElement.lang || '').toLowerCase().startsWith('cs');
}

function copy(cs, en) {
  return isCzech() ? cs : en;
}

function sourceLabel(source) {
  const labels = {
    get_data_inventory: copy('Přehled dat', 'Data inventory'),
    get_profile: copy('Profil', 'Profile'),
    get_meals: copy('Jídla', 'Meals'),
    get_withings_measurements: 'Withings',
    get_oura_daily: 'Oura',
    get_health_summary: copy('Health souhrn', 'Health summary'),
  };
  return labels[source] || source;
}

function applyCopy() {
  document.getElementById('assistantEyebrow').textContent = copy('Tvůj soukromý datový copilot', 'Your private data copilot');
  document.getElementById('assistantHeading').textContent = copy(
    'Ptej se Food Readeru na cokoliv o svých datech.',
    'Ask Food Reader anything about your data.',
  );
  document.getElementById('assistantSupport').textContent = copy(
    'Asistent si umí načíst tvoje jídla, cíle, Oura recovery a spánek, Withings měření i kombinované health trendy.',
    'The assistant can query your meals, targets, Oura recovery and sleep, Withings measurements, and combined health trends.',
  );
  document.getElementById('assistantName').textContent = 'Food Reader AI';
  document.getElementById('assistantPrivacy').textContent = copy(
    'Pouze pro čtení · data jen tvého účtu',
    'Read-only · scoped to your account',
  );
  document.getElementById('clearAssistantButton').textContent = copy('Vymazat chat', 'Clear chat');
  document.getElementById('assistantInput').placeholder = copy(
    'Zeptej se na jídlo, váhu, spánek, recovery, trendy…',
    'Ask about your meals, weight, sleep, recovery, trends…',
  );
  document.getElementById('assistantSendButton').textContent = copy('Odeslat', 'Send');
  document.getElementById('assistantDisclaimer').textContent = copy(
    'Health insighty jsou informativní. Data z wearables a odhady kalorií nejsou přesná fyziologická měření ani lékařská diagnóza.',
    'Health insights are informational. Wearable and calorie estimates are not exact physiological measurements or medical diagnoses.',
  );
}

function loadHistory() {
  if (!storageKey) {
    return [];
  }
  try {
    const parsed = JSON.parse(window.localStorage.getItem(storageKey) || '[]');
    return Array.isArray(parsed) ? parsed.slice(-40) : [];
  } catch {
    return [];
  }
}

function saveHistory() {
  if (!storageKey) {
    return;
  }
  window.localStorage.setItem(storageKey, JSON.stringify(chatHistory.slice(-40)));
}

function scrollToBottom() {
  const target = document.getElementById('assistantMessages');
  target.scrollTop = target.scrollHeight;
}

function renderMessages() {
  const target = document.getElementById('assistantMessages');
  target.innerHTML = '';

  if (!chatHistory.length) {
    const empty = document.createElement('div');
    empty.className = 'assistant-empty';
    empty.textContent = copy(
      'Začni otázkou. Asistent si podle ní sám načte potřebná data z Food Readeru.',
      'Start with a question. The assistant will query the relevant Food Reader data automatically.',
    );
    target.appendChild(empty);
    return;
  }

  chatHistory.forEach((item) => {
    const wrapper = document.createElement('article');
    wrapper.className = `assistant-message ${item.role}`;

    const bubble = document.createElement('div');
    bubble.className = 'assistant-bubble';
    bubble.textContent = item.content;
    wrapper.appendChild(bubble);

    if (item.role === 'assistant' && Array.isArray(item.sources) && item.sources.length) {
      const meta = document.createElement('div');
      meta.className = 'assistant-message-meta';
      item.sources.forEach((source) => {
        const chip = document.createElement('span');
        chip.className = 'assistant-source-chip';
        chip.textContent = sourceLabel(source);
        meta.appendChild(chip);
      });
      wrapper.appendChild(meta);
    }

    target.appendChild(wrapper);
  });
  scrollToBottom();
}

function addThinking() {
  const target = document.getElementById('assistantMessages');
  target.querySelector('.assistant-empty')?.remove();
  const wrapper = document.createElement('article');
  wrapper.id = 'assistantThinking';
  wrapper.className = 'assistant-message assistant';
  wrapper.innerHTML = `
    <div class="assistant-bubble">
      <span class="assistant-thinking" aria-label="Thinking"><span></span><span></span><span></span></span>
    </div>
  `;
  target.appendChild(wrapper);
  scrollToBottom();
}

function removeThinking() {
  document.getElementById('assistantThinking')?.remove();
}

function setSending(value) {
  isSending = value;
  document.getElementById('assistantSendButton').disabled = value;
  document.getElementById('assistantInput').disabled = value;
}

async function sendMessage(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed || isSending) {
    return;
  }

  const status = document.getElementById('assistantStatus');
  const priorHistory = chatHistory.slice(-12).map(({ role, content }) => ({ role, content }));
  chatHistory.push({ role: 'user', content: trimmed });
  saveHistory();
  renderMessages();
  addThinking();
  setSending(true);
  showStatus(status, copy('Načítám relevantní data…', 'Querying relevant data…'), 'info');

  try {
    const response = await apiFetch('/assistant/chat', {
      method: 'POST',
      body: {
        message: trimmed,
        history: priorHistory,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Prague',
        locale: isCzech() ? 'cs' : 'en',
      },
    });
    const payload = await getJsonOrThrow(response, copy('AI asistent selhal', 'AI assistant failed'));
    removeThinking();
    chatHistory.push({
      role: 'assistant',
      content: payload.message || copy('Bez odpovědi.', 'No response.'),
      sources: payload.sources || [],
    });
    saveHistory();
    renderMessages();
    showStatus(
      status,
      payload.available
        ? copy('Odpověď je založená na dostupných datech a použitých zdrojích.', 'Answer generated from available data and queried sources.')
        : payload.message,
      payload.available ? 'success' : 'info',
    );
  } catch (error) {
    removeThinking();
    showStatus(status, error.message, 'danger');
  } finally {
    setSending(false);
    const input = document.getElementById('assistantInput');
    input.focus();
  }
}

async function init() {
  const user = await setupPage();
  if (!user) {
    return;
  }

  const currentUser = getCurrentUserContext();
  storageKey = `food-reader:user:${currentUser.id}:assistant-history`;
  applyCopy();
  chatHistory = loadHistory();
  renderMessages();

  const form = document.getElementById('assistantForm');
  const input = document.getElementById('assistantInput');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const value = input.value;
    input.value = '';
    await sendMessage(value);
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  document.getElementById('clearAssistantButton').addEventListener('click', () => {
    chatHistory = [];
    saveHistory();
    renderMessages();
    showStatus(document.getElementById('assistantStatus'), copy('Chat byl vymazán.', 'Chat cleared.'), 'success');
  });

  document.querySelectorAll('#assistantSuggestions button').forEach((button) => {
    button.addEventListener('click', () => {
      void sendMessage(isCzech() ? button.dataset.promptCs : button.dataset.promptEn);
    });
  });

  window.addEventListener('food-reader:localechange', () => {
    applyCopy();
    renderMessages();
  });
}

document.addEventListener('DOMContentLoaded', init);
