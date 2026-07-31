/* ============================================================
   Bilel Khlaifia | portfolio behaviour
   Progressive enhancement only. The page works with JS disabled.
   ============================================================ */

(function () {
  'use strict';

  /* ---------- theme ---------- */

  var root = document.documentElement;
  var toggle = document.getElementById('theme-toggle');
  var STORE_KEY = 'bk-theme';

  function apply(theme) {
    root.setAttribute('data-theme', theme);
    if (toggle) {
      var dark = theme === 'dark';
      toggle.setAttribute('aria-pressed', String(dark));
      toggle.setAttribute('aria-label', 'Switch to ' + (dark ? 'light' : 'dark') + ' theme');
    }
  }

  var stored = null;
  try { stored = localStorage.getItem(STORE_KEY); } catch (e) { /* private mode */ }

  if (stored === 'dark' || stored === 'light') {
    apply(stored);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    apply('dark');
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      apply(next);
      try { localStorage.setItem(STORE_KEY, next); } catch (e) { /* ignore */ }
    });
  }

  // follow the OS if the visitor has never chosen explicitly
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var onChange = function (e) {
      var saved = null;
      try { saved = localStorage.getItem(STORE_KEY); } catch (err) { /* ignore */ }
      if (!saved) apply(e.matches ? 'dark' : 'light');
    };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }

  /* ---------- current year ---------- */

  var yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  /* ---------- active nav on scroll ---------- */

  var links = Array.prototype.slice.call(document.querySelectorAll('.nav a'));
  var sections = links
    .map(function (a) { return document.querySelector(a.getAttribute('href')); })
    .filter(Boolean);

  if ('IntersectionObserver' in window && sections.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (a) {
          a.classList.toggle('active', a.getAttribute('href') === '#' + entry.target.id);
        });
      });
    }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });

    sections.forEach(function (s) { io.observe(s); });
  }

  /* ---------- live star counts ---------- */

  var CACHE_KEY = 'bk-repos';
  var TTL = 6 * 60 * 60 * 1000; // 6 hours

  function paint(map) {
    document.querySelectorAll('[data-repo]').forEach(function (card) {
      var name = card.getAttribute('data-repo');
      var el = card.querySelector('[data-stars]');
      if (el && typeof map[name] === 'number') el.textContent = String(map[name]);
    });
  }

  function readCache() {
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (Date.now() - parsed.t > TTL) return null;
      return parsed.d;
    } catch (e) { return null; }
  }

  var cached = readCache();
  if (cached) {
    paint(cached);
  } else if (window.fetch) {
    fetch('https://api.github.com/users/khlaifiabilel/repos?per_page=100&sort=updated', {
      headers: { Accept: 'application/vnd.github+json' }
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (repos) {
        if (!Array.isArray(repos)) return;
        var map = {};
        repos.forEach(function (r) { map[r.name] = r.stargazers_count; });
        paint(map);
        try {
          sessionStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), d: map }));
        } catch (e) { /* ignore */ }
      })
      .catch(function () {
        /* Keep the server-rendered numbers; no visible failure. */
      });
  }
})();
