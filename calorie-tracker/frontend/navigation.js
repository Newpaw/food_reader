import './mobile-ux.js?v=20260809-4';

const MOBILE_POLISH_VERSION = '20260809-2';
const RESPONSIVE_FIX_VERSION = '20260809-3';

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
    desktop: { en: 'Add Meal', cs: 'Přidat jídlo' },
    mobile: { en: 'Add', cs: 'Přidat' },
  },
  {
    id: 'history',
    href: 'history.html',
    desktop: { en: 'History', cs: 'Historie' },
    mobile: { en: 'History', cs: 'Historie' },
  },
  {
    id: 'metrics',
    href: 'metrics.html',
    desktop: { en: 'Metrics', cs: 'Přehled' },
    mobile: { en: 'Metrics', cs: 'Přehled' },
  },
  {
    id: 'health',
    href: 'health.html',
    desktop: { en: 'Health', cs: 'Zdraví' },
    mobile: { en: 'Health', cs: 'Zdraví' },
  },
  {
    id: 'assistant',
    href: 'assistant.html',
    desktop: { en: 'AI Assistant', cs: 'AI asistent' },
    mobile: { en: 'AI', cs: 'AI' },
  },
  {
    id: 'profile',
    href: 'profile.html',
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
    return `<a href="${item.href}" data-nav="${item.id}"${activeClass}${currentAttribute}>${label}</a>`;
  }).join('');
}

function ensureMobileNavigationStyle() {
  if (document.getElementById('food-reader-global-navigation-style')) {
    return;
  }

  const style = document.createElement('style');
  style.id = 'food-reader-global-navigation-style';
  style.textContent = `
    .bottom-nav {
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }

    .bottom-nav a {
      min-width: 0;
      padding-left: 0.2rem;
      padding-right: 0.2rem;
      font-size: clamp(0.64rem, 2.6vw, 0.78rem);
      white-space: nowrap;
    }

    @media (max-width: 979px) {
      .bottom-nav {
        position: fixed !important;
        left: 0.45rem !important;
        right: 0.45rem !important;
        bottom: max(0.45rem, env(safe-area-inset-bottom, 0px)) !important;
        width: auto !important;
        max-width: none !important;
        transform: none !important;
        z-index: 1000 !important;
        display: grid !important;
        grid-template-columns: repeat(6, minmax(0, 1fr)) !important;
        gap: 0.18rem !important;
        padding: 0.28rem !important;
        border-radius: 1.35rem !important;
        overflow: hidden !important;
        visibility: visible !important;
        opacity: 1 !important;
      }

      .bottom-nav a {
        min-width: 0 !important;
        min-height: 2.7rem;
        display: grid;
        place-items: center;
        padding: 0.4rem 0.08rem !important;
        font-size: clamp(0.62rem, 2.5vw, 0.78rem) !important;
        line-height: 1.05;
      }

      body[data-page] .page {
        padding-bottom: calc(5.5rem + env(safe-area-inset-bottom, 0px));
      }
    }

    @media (min-width: 980px) {
      .bottom-nav { display: none !important; }
    }
  `;
  document.head.appendChild(style);
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

    if (nav.parentElement !== document.body) {
      document.body.appendChild(nav);
    }
  });

  ensureMobileNavigationStyle();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', renderNavigation, { once: true });
} else {
  renderNavigation();
}

window.addEventListener('food-reader:localechange', renderNavigation);
