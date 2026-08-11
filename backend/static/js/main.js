// Small interactive polish
document.addEventListener('DOMContentLoaded', () => {
  // Smooth-scroll for in-page anchors
  document.querySelectorAll('a[href*="#"]').forEach(a => {
    const url = new URL(a.href, window.location.href);
    if (url.pathname === window.location.pathname && url.hash) {
      a.addEventListener('click', (e) => {
        const el = document.querySelector(url.hash);
        if (el) { e.preventDefault(); el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      });
    }
  });

  // Auto-dismiss flashes after 5s
  setTimeout(() => {
    document.querySelectorAll('.csp-flash').forEach(el => {
      const btn = el.querySelector('.btn-close');
      if (btn) btn.click();
    });
  }, 5000);
});
