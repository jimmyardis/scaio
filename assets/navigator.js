/*
 * SCAIO Policy Navigator — site loader.
 *
 * Every page loads this file; this file is the ONE place the navigator's
 * backend origin is configured. embed.js resolves the chat widget against
 * its own script URL, so changing NAVIGATOR_ORIGIN here re-points the whole
 * site — no need to touch the individual pages again.
 */
(function () {
  var NAVIGATOR_ORIGIN = 'https://web-production-015441.up.railway.app';

  var s = document.createElement('script');
  s.src = NAVIGATOR_ORIGIN + '/frontend/embed.js';
  s.async = true;
  document.head.appendChild(s);
})();
