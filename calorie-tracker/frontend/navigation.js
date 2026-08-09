import './mobile-ux.js?v=20260809-4';

const MOBILE_POLISH_VERSION = '20260809-3';
const RESPONSIVE_FIX_VERSION = '20260809-5';

function ensureSharedStylesheets() {
  // Health owns its responsive layout in health.css. Do not stack the older
  // generic responsive layers on top of it; that was the source of conflicting
  // breakpoints and horizontal overflow on Android.
  if (document.body?.dataset.page === 'health') {
    return;
  }

  if (!document.getElementById('food-reader-mobile-polish')) {
    const polish = document.createElement('link');
    polish.id = 'food-reader-mobile-polish';
    polish.rel = 'stylesheet';
    polish.href = `mobile-polish.css?v=${MOBILE_POLISH_VERSION}`;
    document.head.appendChild(polish);
  }

  if (!document.getElementById('food-reader-responsive-fix')) {
    const responsiveFix = document.createElement('link');
    responsiveFix.id = 'food-reader-responsive-fix';
    responsiveFix.rel = 'stylesheet';
    responsiveFix.href = `responsive-fix.css?v=${RESPONSIVE_FIX_VERSION}`;
    document.head.appendChild(responsiveFix);
  }
}

ensureSharedStylesheets();

const NAV_ITEMS = [
  {
    id: 'add',
    href: 'index.html',
    icon: '<path d="M12 5v14M5 12h14"/>',
    desktop: { en: 'Add Meal', cs: 'Přidat jídlo' },
    mobile: { en: 'Add', cs: 'Přidat' },
  },
  {
    id: 'history',
    href: 'history.html',
    icon: '<path d="M12 7v5l3 2"/><circle cx="12" cy="12" r="8"/>',
    desktop: { en: 'History', cs: 'Historie' },
    mobile: { en: 'History', cs: 'Historie' },
  },
  {
    id: 'metrics',
    href: 'metrics.html',
    icon: '<path d="M5 19V9M12 19V5M19 19v-7"/>',
    desktop: { en: 'Metrics', cs: 'Přehled' },
    mobile: { en: 'Metrics', cs: 'Přehled' },
  },
  {
    id: 'health',
    href: 'health.html',
    icon: '<path d="M20.8 8.4c0 5-8.8 10.1-8.8 10.1S3.2 13.4 3.2 8.4A4.2 4.2 0 0 1 12 5a4.2 4.2 0 0 1 8.8 3.4Z"/>',
    desktop: { en: 'Health', cs: 'Zdraví' },
    mobile: { en: 'Health', cs: 'Zdraví' },
  },
  {
    id: 'assistant',
    href: 'assistant.html',
    icon: '<path d="m12 3 1.2 4.1L17 9l-3.8 1.9L12 15l-1.2-4.1L7 9l3.8-1.9L12 3ZM18.5 15l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z"/>',
    desktop: { en: 'AI Assistant', cs: 'AI asistent' },
    mobile: { en: 'AI', cs: 'AI' },
  },
  {
    id: 'profile',
    href: 'profile.html',
    icon: '<circle cx="12" cy="8" r="3"/><path d="M5.5 20a6.5 6.5 0 0 1 13 0"/>',
    desktop: { en: 'Profile', cs: 'Profil' },
    mobile: { en: 'Profile', cs: 'Profil' },
  },
];

const PAGE_BY_FILE = {
  '': 'add',
  'index.html': 'add',
  'history.html': 'history',
  'metrics.html': 'metrics',
  'health.html': 'health',
  'assistant.html': 'assistant',
  'profile.html': 'profile',
};

function getLocale() {
  try {
    const storedLocale = window.localStorage.getItem('food-reader:locale');
    if (storedLocale === 'cs' || storedLocale === 'en') {
      return storedLocale;
    }
  } catch {
    // Fall through to the same browser-language default used by common.js.
  }

  const browserLocale = (window.navigator?.language || '').toLowerCase();
  if (browserLocale.startsWith('cs')) {
    return 'cs';
  }

  const documentLocale = (document.documentElement.lang || '').toLowerCase();
  return documentLocale.startsWith('cs') ? 'cs' : 'en';
}

function getCurrentPage() {
  const bodyPage = document.body?.dataset.page;
  if (NAV_ITEMS.some((item) => item.id === bodyPage)) {
    return bodyPage;
  }

  const filename = window.location.pathname.split('/').pop() || '';
  return PAGE_BY_FILE[filename] || null;
}

function renderLinks(mode, locale, currentPage) {
  return NAV_ITEMS.map((item) => {
    const label = item[mode][locale];
    const isCurrent = item.id === currentPage;
    const currentAttribute = isCurrent ? ' aria-current="page"' : '';
    const activeClass = isCurrent ? ' class="active"' : '';
    const accessibleLabel = item.desktop[locale];
    const mobileContents = `
      <svg class="bottom-nav-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${item.icon}</svg>
      <span>${label}</span>
    `;
    const contents = mode === 'mobile' ? mobileContents : label;
    const ariaLabel = mode === 'mobile' ? ` aria-label="${accessibleLabel}"` : '';
    return `<a href="${item.href}" data-nav="${item.id}"${activeClass}${currentAttribute}${ariaLabel}>${contents}</a>`;
  }).join('');
}

function renderNavigation() {
  const locale = getLocale();
  const currentPage = getCurrentPage();

  document.querySelectorAll('.desktop-nav').forEach((nav) => {
    nav.setAttribute('aria-label', locale === 'cs' ? 'Hlavní navigace' : 'Primary navigation');
    nav.innerHTML = renderLinks('desktop', locale, currentPage);
  });

  document.querySelectorAll('.bottom-nav').forEach((nav) => {
    nav.setAttribute('aria-label', locale === 'cs' ? 'Mobilní navigace' : 'Mobile navigation');
    nav.innerHTML = renderLinks('mobile', locale, currentPage);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', renderNavigation, { once: true });
} else {
  renderNavigation();
}

window.addEventListener('food-reader:localechange', renderNavigation);
