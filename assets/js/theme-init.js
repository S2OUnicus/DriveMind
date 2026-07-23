(() => {
  'use strict';
  const key = 'drivemind-site-theme';
  let theme = 'light';
  try {
    const stored = localStorage.getItem(key);
    if (stored === 'dark' || stored === 'light') {
      theme = stored;
    } else if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
      theme = 'dark';
    }
  } catch (_) {
    theme = 'light';
  }
  document.documentElement.dataset.theme = theme;
})();
