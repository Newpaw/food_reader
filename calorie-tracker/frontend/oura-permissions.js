import { apiFetch } from './common.js?v=20260403-11';

let needsUpgrade = false;

function isCzech() {
  return (document.documentElement.lang || '').toLowerCase().startsWith('cs');
}

function upgradeLabel() {
  return isCzech() ? 'Povolit více Oura dat' : 'Enable more Oura data';
}

function applyUpgradeState() {
  if (!needsUpgrade) return;
  const button = document.getElementById('connectOuraButton');
  if (!button) return;
  button.hidden = false;
  button.textContent = upgradeLabel();
  button.title = isCzech()
    ? 'Doplní oprávnění pro tep, SpO₂, session a tagy. Stávající data zůstanou zachovaná.'
    : 'Adds permissions for heart rate, SpO₂, sessions and tags. Existing data stays intact.';
}

async function refreshPermissionState() {
  try {
    const response = await apiFetch('/oura/status');
    if (!response.ok) return;
    const status = await response.json();
    needsUpgrade = Boolean(status.connected && status.needs_reauthorization);
    applyUpgradeState();
  } catch {
    // The main Health screen owns connectivity errors. This helper is optional UX.
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await refreshPermissionState();

  const button = document.getElementById('connectOuraButton');
  if (button) {
    new MutationObserver(() => applyUpgradeState()).observe(button, {
      attributes: true,
      attributeFilter: ['hidden'],
    });
  }

  window.addEventListener('food-reader:localechange', applyUpgradeState);
});
