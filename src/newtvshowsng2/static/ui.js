(() => {
  for (const nav of document.querySelectorAll('.nav')) {
    const links = [...nav.querySelectorAll('a')];
    let hovered = null;

    function updateHover() {
      if (!hovered || hovered.hasAttribute('aria-current')) {
        nav.classList.remove('nav-hover-visible');
        return;
      }
      const bounds = nav.getBoundingClientRect();
      const target = hovered.getBoundingClientRect();
      nav.style.setProperty('--nav-hover-left', `${target.left - bounds.left - nav.clientLeft}px`);
      nav.style.setProperty('--nav-hover-width', `${target.width}px`);
      if (!nav.classList.contains('nav-hover-visible')) {
        // Beim ersten Eintritt beginnt die Bewegung direkt am angesteuerten Link.
        getComputedStyle(nav, '::before').transform;
      }
      nav.classList.add('nav-hover-visible');
    }

    function updateCurrent() {
      const view = ['#history', '#media-import'].includes(location.hash) ? location.hash : '#overview';
      for (const link of links) {
        const destination = new URL(link.href);
        const current = destination.origin === location.origin
          && destination.pathname.replace(/\/+$/, '') === location.pathname.replace(/\/+$/, '')
          && (!destination.hash || destination.hash === view);
        if (current) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      }
      updateHover();
    }

    function clearHover() {
      hovered = null;
      updateHover();
    }

    for (const link of links) {
      link.addEventListener('pointerenter', event => {
        if (event.pointerType === 'touch') return;
        hovered = link;
        updateHover();
      });
    }
    nav.addEventListener('pointerleave', clearHover);
    nav.addEventListener('pointercancel', clearHover);
    window.addEventListener('blur', clearHover);
    window.addEventListener('hashchange', updateCurrent);
    window.addEventListener('pageshow', updateCurrent);
    const observer = new ResizeObserver(updateHover);
    observer.observe(nav);
    for (const link of links) observer.observe(link);
    nav.classList.add('nav-enhanced');
    updateCurrent();
  }
})();

(() => {
  const form = document.querySelector('[data-log-filters]');
  if (!form) return;
  const results = document.querySelector('[data-log-results]');
  const count = document.querySelector('[data-log-count]');
  const refresh = document.querySelector('.log-actions .refresh');
  const search = form.elements.namedItem('q');
  let timer;
  let request = null;
  let composing = false;

  function cancelPending() {
    clearTimeout(timer);
    request?.abort();
    request = null;
    results.removeAttribute('aria-busy');
  }

  async function applyFilters() {
    const url = new URL(form.action);
    url.search = new URLSearchParams(new FormData(form)).toString();
    const current = new AbortController();
    request = current;
    const timeout = setTimeout(() => current.abort(), 10000);
    results.setAttribute('aria-busy', 'true');
    count.textContent = 'Log wird gefiltert.';
    try {
      const response = await fetch(url, { cache: 'no-store', signal: current.signal });
      if (!response.ok) throw new Error('Log nicht verfügbar');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (request !== current) return;
      const incoming = page.querySelector('[data-log-results]');
      const incomingCount = page.querySelector('[data-log-count]');
      const incomingRefresh = page.querySelector('.log-actions .refresh');
      if (!incoming || !incomingCount || !incomingRefresh) throw new Error('Log unvollständig');

      // Nur Ergebnisse ersetzen, damit Fokus und Textauswahl im Suchfeld erhalten bleiben.
      results.replaceChildren(...incoming.childNodes);
      count.textContent = incomingCount.textContent;
      refresh.href = incomingRefresh.getAttribute('href');
      history.replaceState(null, '', url);
    } catch {
      // Bei einem Abruffehler bleibt derselbe Filter über die normale GET-Seite erreichbar.
      if (request === current) location.assign(url);
    } finally {
      clearTimeout(timeout);
      if (request === current) {
        request = null;
        results.removeAttribute('aria-busy');
      }
    }
  }

  function schedule(delay = 0) {
    cancelPending();
    if (delay) timer = setTimeout(applyFilters, delay);
    else applyFilters();
  }

  for (const select of form.querySelectorAll('select')) {
    select.addEventListener('change', () => schedule());
  }
  search.addEventListener('input', event => {
    if (composing || event.isComposing) cancelPending();
    else schedule(search.value ? 350 : 0);
  });
  search.addEventListener('compositionstart', () => {
    composing = true;
    cancelPending();
  });
  search.addEventListener('compositionend', () => {
    composing = false;
    schedule(350);
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!composing) schedule();
  });
})();

(() => {
  const feedback = [...document.querySelectorAll('[data-run-feedback][data-running="true"]')];
  if (!feedback.length) return;

  async function updateStatus() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch("/", { cache: "no-store", signal: controller.signal });
      if (!response.ok) throw new Error("Status nicht verfügbar");
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const remoteFeedback = [...page.querySelectorAll("[data-run-feedback]")];
      if (remoteFeedback.length !== 2) throw new Error("Status unvollständig");

      // Tabellen und Filter bleiben erhalten, damit laufende Prüfungen
      // die aktuelle Bedienung nicht durch neue Ergebnisse unterbrechen.
      const busy = remoteFeedback.some(node => node.dataset.running === "true");
      for (const button of document.querySelectorAll("[data-run-start]")) button.disabled = busy;
      for (const current of feedback) {
        const incoming = remoteFeedback.find(node => node.dataset.runFeedback === current.dataset.runFeedback);
        current.dataset.running = incoming.dataset.running;
        const message = current.querySelector("[data-run-message]");
        const text = incoming.dataset.running === "true"
          ? incoming.querySelector("[data-run-message]").textContent
          : "Der Lauf ist beendet. Lade die neuen Ergebnisse mit «Ansicht aktualisieren».";
        if (message.textContent !== text) message.textContent = text;
      }
      if (feedback.some(node => node.dataset.running === "false")) {
        document.querySelector("[data-results-available]").hidden = false;
      }
      if (busy) setTimeout(updateStatus, 3000);
    } catch {
      for (const current of feedback) {
        const message = current.querySelector("[data-run-message]");
        const text = "Der Laufstatus konnte nicht geladen werden. Prüfe den aktuellen Stand mit «Ansicht aktualisieren».";
        if (message.textContent !== text) message.textContent = text;
      }
      setTimeout(updateStatus, 5000);
    } finally {
      clearTimeout(timeout);
    }
  }
  setTimeout(updateStatus, 3000);
})();
