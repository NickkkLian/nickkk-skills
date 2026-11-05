// Read the saved display preference before the first paint.
(() => {
  try {
    const saved = localStorage.getItem('nickkk-skills-theme') || localStorage.getItem('nl-scheme');
    if (saved === 'dark' || saved === 'light') document.documentElement.dataset.theme = saved;
  } catch {}
})();
