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
  const documentLocale = (document.documentElement.lang || '').toLowerCase();
  if (documentLocale.startsWith('cs')) {
    return 'cs';
  }
  if (documentLocale.startsWith('en')) {
    return 'en';
  }

  try {
    return window.localStorage.getItem('food-reader:locale') === 'cs' ? 'cs' : 'en';
  } catch {
    return 'en';
  }
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
  });

  ensureMobileNavigationStyle();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', renderNavigation, { once: true });
} else {
  renderNavigation();
}

window.addEventListener('food-reader:localechange', renderNavigation);
