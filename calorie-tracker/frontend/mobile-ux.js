const MOBILE_QUERY = '(max-width: 759px)';
const mobileMedia = window.matchMedia(MOBILE_QUERY);

function isCzech() {
  return (document.documentElement.lang || '').toLowerCase().startsWith('cs');
}

function setButtonText(button, text, ariaLabel = text) {
  if (!button) return;
  button.textContent = text;
  button.setAttribute('aria-label', ariaLabel);
}

function applyCompactRangeCopy() {
  const mobile = mobileMedia.matches;
  const cs = isCzech();

  document.querySelectorAll('[data-days]').forEach((button) => {
    const days = button.dataset.days;
    const shortLabels = cs
      ? { '0': 'Dnes', '6': '7 dní', '29': '30 dní', '89': '90 dní' }
      : { '0': 'Today', '6': '7 days', '29': '30 days', '89': '90 days' };
    const longLabels = cs
      ? { '0': 'Dnes', '6': 'Posledních 7 dní', '29': 'Posledních 30 dní', '89': 'Posledních 90 dní' }
      : { '0': 'Today', '6': 'Last 7 days', '29': 'Last 30 days', '89': 'Last 90 days' };
    const label = mobile ? shortLabels[days] : longLabels[days];
    if (label) setButtonText(button, label, longLabels[days] || label);
  });

  const historyCustom = document.getElementById('historyToggleCustomRange');
  const metricsCustom = document.getElementById('metricsToggleCustomRange');
  if (mobile) {
    setButtonText(historyCustom, cs ? 'Vlastní' : 'Custom', cs ? 'Vlastní datumy' : 'Custom dates');
    setButtonText(metricsCustom, cs ? 'Vlastní' : 'Custom', cs ? 'Vlastní datumy' : 'Custom dates');
  } else {
    setButtonText(historyCustom, cs ? 'Vlastní datumy' : 'Custom dates');
    setButtonText(metricsCustom, cs ? 'Vlastní datumy' : 'Custom dates');
  }
}

function applyHealthMobileCopy() {
  const cs = isCzech();
  const mobile = mobileMedia.matches;
  const coachHeading = document.getElementById('coachHeading');
  const refreshButton = document.getElementById('generateCoachButton');

  if (coachHeading) {
    coachHeading.textContent = mobile
      ? (cs ? 'Co teď?' : 'What now?')
      : (cs ? 'Co mám udělat teď?' : 'What should I do now?');
  }

  if (refreshButton) {
    setButtonText(
      refreshButton,
      mobile ? (cs ? 'Obnovit' : 'Refresh') : (cs ? 'Obnovit radu' : 'Refresh advice'),
    );
  }

  document.querySelectorAll('[data-health-days]').forEach((button) => {
    const raw = Number(button.dataset.healthDays || 0) + 1;
    setButtonText(button, cs ? `${raw} dní` : `${raw} days`);
  });
}

function applyResponsiveCopy() {
  applyCompactRangeCopy();
  applyHealthMobileCopy();
}

function syncAssistantViewport() {
  if (document.body?.dataset.page !== 'assistant') return;
  const viewport = window.visualViewport;
  const height = viewport?.height || window.innerHeight;
  const top = viewport?.offsetTop || 0;
  document.documentElement.style.setProperty('--assistant-vv-height', `${Math.round(height)}px`);
  document.documentElement.style.setProperty('--assistant-vv-top', `${Math.round(top)}px`);
}

function setupAssistantViewport() {
  if (document.body?.dataset.page !== 'assistant') return;

  const input = document.getElementById('assistantInput');
  if (!input) return;

  const markFocused = () => {
    document.body.classList.add('assistant-input-focused');
    requestAnimationFrame(syncAssistantViewport);
  };
  const markBlurred = () => {
    window.setTimeout(() => {
      document.body.classList.remove('assistant-input-focused');
      syncAssistantViewport();
    }, 120);
  };

  input.addEventListener('focus', markFocused);
  input.addEventListener('blur', markBlurred);
  window.visualViewport?.addEventListener('resize', syncAssistantViewport);
  window.visualViewport?.addEventListener('scroll', syncAssistantViewport);
  window.addEventListener('resize', syncAssistantViewport);
  syncAssistantViewport();
}

function init() {
  applyResponsiveCopy();
  setupAssistantViewport();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  init();
}

window.addEventListener('food-reader:localechange', () => {
  requestAnimationFrame(applyResponsiveCopy);
});

mobileMedia.addEventListener?.('change', () => {
  applyResponsiveCopy();
  syncAssistantViewport();
});
