// Header shadow on scroll, mobile menu and language switch (shared by every page)
(() => {
  const header = document.querySelector('body > header');
  const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 40);
  onScroll(); window.addEventListener('scroll', onScroll, {passive:true});

  // Mobile menu
  const menuBtn = document.getElementById('menuBtn'), navLinks = document.getElementById('navLinks');
  const labelOpen = menuBtn.dataset.labelOpen || 'Open menu', labelClose = menuBtn.dataset.labelClose || 'Close menu';
  const setMenu = open => {
    navLinks.classList.toggle('open', open);
    menuBtn.setAttribute('aria-expanded', open);
    menuBtn.setAttribute('aria-label', open ? labelClose : labelOpen);
  };
  menuBtn.addEventListener('click', () => setMenu(!navLinks.classList.contains('open')));
  navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && navLinks.classList.contains('open')) { setMenu(false); menuBtn.focus(); } });

  // Links like /es/#faq: the browser jumps before fonts load and the page reflows, so jump again once loaded
  if (location.hash.length > 1) addEventListener('load', () => {
    try { const t = document.querySelector(decodeURIComponent(location.hash)); if (t) t.scrollIntoView({behavior: 'instant', block: 'start'}); } catch (e) {}
  });

  // Language switch: remember the choice and keep the visitor's place on the page
  document.querySelectorAll('.lang-switch a[data-lang]').forEach(a => a.addEventListener('click', () => {
    try { localStorage.setItem('mc-lang', a.dataset.lang); } catch (e) {}
    if (location.hash && !a.href.includes('#')) a.href += location.hash;
  }));
})();
