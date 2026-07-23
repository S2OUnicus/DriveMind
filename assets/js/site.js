(() => {
  'use strict';

  const THEME_KEY = 'drivemind-site-theme';
  const root = document.documentElement;
  const toggle = document.getElementById('theme-toggle');
  const themeMeta = document.querySelector('meta[name="theme-color"]');

  const setTheme = (theme, persist = true) => {
    const normalized = theme === 'dark' ? 'dark' : 'light';
    root.dataset.theme = normalized;
    if (persist) {
      try { localStorage.setItem(THEME_KEY, normalized); } catch (_) {}
    }
    if (toggle) {
      const isDark = normalized === 'dark';
      toggle.setAttribute('aria-label', isDark ? 'lightmodeに切り替える' : 'darkmodeに切り替える');
      toggle.setAttribute('title', isDark ? 'lightmodeに切り替える' : 'darkmodeに切り替える');
      const label = toggle.querySelector('[data-theme-label]');
      if (label) label.textContent = isDark ? 'lightmode' : 'darkmode';
      const icon = toggle.querySelector('[data-theme-icon]');
      if (icon) icon.setAttribute('uk-icon', isDark ? 'icon: sun' : 'icon: moon');
    }
    if (themeMeta) themeMeta.setAttribute('content', normalized === 'dark' ? '#071827' : '#eaf6ff');
  };

  setTheme(root.dataset.theme || 'light', false);
  toggle?.addEventListener('click', () => setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark'));

  document.getElementById('back-to-top')?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  const topButton = document.getElementById('back-to-top');
  const updateTopButton = () => {
    if (!topButton) return;
    topButton.classList.toggle('is-visible', window.scrollY > 420);
  };
  updateTopButton();
  window.addEventListener('scroll', updateTopButton, { passive: true });

  document.body.addEventListener('htmx:responseError', () => {
    if (window.UIkit) UIkit.notification({ message: '内容の読み込みに失敗しました。', status: 'danger' });
  });

  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', () => {
      const offcanvas = document.getElementById('mobile-menu');
      if (offcanvas && window.UIkit) UIkit.offcanvas(offcanvas).hide();
    });
  });
})();
