/* SCAIO Learn · shared deck navigation logic
   Loaded by every primer-NN-*.html under /learn/ */

(function () {
  const slides = Array.from(document.querySelectorAll('.slide'));
  const counter = document.getElementById('counter');
  let current = 0;

  function go(n) {
    current = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach((s, i) => s.classList.toggle('active', i === current));
    if (counter) counter.textContent = `${current + 1} / ${slides.length}`;
  }

  // Button controls
  const prev = document.getElementById('prev');
  const next = document.getElementById('next');
  if (prev) prev.addEventListener('click', () => go(current - 1));
  if (next) next.addEventListener('click', () => go(current + 1));

  // Keyboard
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); go(current + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp')                { e.preventDefault(); go(current - 1); }
    else if (e.key === 'Home')                                            { e.preventDefault(); go(0); }
    else if (e.key === 'End')                                             { e.preventDefault(); go(slides.length - 1); }
    else if (e.key === 'Escape')                                          { try { window.parent.postMessage({ type: 'close-fullscreen' }, '*'); } catch (e) {} }
  });

  // Parent-frame navigation
  window.addEventListener('message', (e) => {
    if (!e.data || typeof e.data !== 'object') return;
    if (e.data.type === 'navigate') {
      if      (e.data.direction === 'prev') go(current - 1);
      else if (e.data.direction === 'next') go(current + 1);
    }
  });

  // Touch swipe (mobile)
  let touchStartX = null;
  document.addEventListener('touchstart', (e) => { touchStartX = e.changedTouches[0].clientX; });
  document.addEventListener('touchend',   (e) => {
    if (touchStartX === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) go(current + (dx < 0 ? 1 : -1));
    touchStartX = null;
  });

  go(0);
})();
