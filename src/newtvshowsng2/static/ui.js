(() => {
  function refreshOnReturn(refresh) {
    const feedback = document.querySelector('[data-return-feedback]');
    const retry = feedback.querySelector('button');
    let updatedAt = Date.now();
    let attemptedAt = 0;
    let pending = false;
    let deferred = false;

    function updated() {
      updatedAt = Date.now();
      deferred = false;
      feedback.hidden = true;
    }

    async function update(force = false) {
      if (document.hidden || pending || (!force && Date.now() - updatedAt < 60000)) return;
      // Sichtbarkeit und Fensterfokus können dieselbe Rückkehr nacheinander melden.
      if (!force && !deferred && Date.now() - attemptedAt < 1000) return;
      attemptedAt = Date.now();
      pending = true;
      retry.disabled = true;
      try {
        if (await refresh()) updated();
        else deferred = true;
      } catch {
        feedback.hidden = false;
      } finally {
        pending = false;
        retry.disabled = false;
      }
    }

    document.addEventListener('visibilitychange', () => update());
    window.addEventListener('focus', () => update());
    window.addEventListener('pageshow', event => {
      if (event.persisted) update();
    });
    // Ein fokussierter Tabellenbutton oder markierter Text darf beim Ersetzen nicht verschwinden.
    for (const event of ['focusout', 'selectionchange']) {
      document.addEventListener(event, () => {
        if (deferred) setTimeout(() => update(), 0);
      });
    }
    retry.addEventListener('click', () => update(true));
    return updated;
  }

  function canReplace(regions) {
    if (document.hidden) return false;
    if (regions.some(region => region.contains(document.activeElement))) return false;
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed) return true;
    for (let index = 0; index < selection.rangeCount; index++) {
      if (regions.some(region => selection.getRangeAt(index).intersectsNode(region))) return false;
    }
    return true;
  }

  function preservePosition(change) {
    const x = scrollX;
    const y = scrollY;
    const navigationBottom = document.querySelector('.topbar').getBoundingClientRect().bottom;
    const anchors = [...document.querySelectorAll('[data-row-key]')]
      .filter(row => row.getClientRects().length && row.getBoundingClientRect().bottom > navigationBottom)
      .map(row => ({ key: row.dataset.rowKey, view: row.closest('.view').id, top: row.getBoundingClientRect().top }));
    change();
    for (const anchor of anchors) {
      const row = [...document.getElementById(anchor.view).querySelectorAll('[data-row-key]')]
        .find(candidate => candidate.dataset.rowKey === anchor.key);
      if (row) {
        scrollTo(x, y + row.getBoundingClientRect().top - anchor.top);
        return;
      }
    }
    scrollTo(x, y);
  }

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

  function initialiseLog() {
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

    async function applyFilters(automatic = false) {
      timer = null;
      const url = new URL(automatic ? location.href : form.action);
      if (!automatic) url.search = new URLSearchParams(new FormData(form)).toString();
      const current = new AbortController();
      request = current;
      const timeout = setTimeout(() => current.abort(), 10000);
      results.setAttribute('aria-busy', 'true');
      if (!automatic) count.textContent = 'Log wird gefiltert.';
      try {
        const response = await fetch(url, { cache: 'no-store', signal: current.signal });
        if (!response.ok) throw new Error('Log nicht verfügbar');
        const page = new DOMParser().parseFromString(await response.text(), 'text/html');
        if (request !== current) return;
        const incoming = page.querySelector('[data-log-results]');
        const incomingCount = page.querySelector('[data-log-count]');
        const incomingRefresh = page.querySelector('.log-actions .refresh');
        if (!incoming || !incomingCount || !incomingRefresh) throw new Error('Log unvollständig');
        if (automatic && !canReplace([results])) return false;

        // Nur Ergebnisse ersetzen, damit Fokus und Textauswahl im Suchfeld erhalten bleiben.
        preservePosition(() => {
          results.replaceChildren(...incoming.childNodes);
          count.textContent = incomingCount.textContent;
          refresh.href = incomingRefresh.getAttribute('href');
          history.replaceState(null, '', url);
        });
        markUpdated();
        return true;
      } catch {
        // Bei einem Abruffehler bleibt derselbe Filter über die normale GET-Seite erreichbar.
        if (request === current) {
          if (automatic) throw new Error('Log nicht verfügbar');
          location.assign(url);
        }
        return false;
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

    const markUpdated = refreshOnReturn(() => {
      if (request || timer || composing || !canReplace([results])) return false;
      return applyFilters(true);
    });

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
  }

  function initialiseResolutionFilters(filters) {
    const overview = document.getElementById('overview-view');
    const storageKey = 'newtvshowsng2.feed.resolutions';
    const selection = new Map();
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey));
      if (saved && typeof saved === 'object' && !Array.isArray(saved)) {
        for (const [resolution, checked] of Object.entries(saved)) {
          if (typeof checked === 'boolean') selection.set(resolution, checked);
        }
      }
    } catch {
      // Gesperrter Browserspeicher oder ungültige Werte dürfen die Anzeige nicht blockieren.
    }

    function apply() {
      for (const group of overview.querySelectorAll('.variant-links')) {
        const links = [...group.querySelectorAll('[data-resolution]')];
        for (const link of links) link.hidden = selection.get(link.dataset.resolution) === false;
        group.querySelector('.resolution-empty').hidden = links.some(link => !link.hidden);
      }
    }

    function update() {
      const available = new Map([...overview.querySelectorAll('[data-resolution]')]
        .map(link => [link.dataset.resolution, Number(link.dataset.resolutionRank)]));
      for (const label of filters.querySelectorAll('label')) label.remove();
      for (const [resolution] of [...available].sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]))) {
        const label = document.createElement('label');
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.value = resolution;
        input.checked = selection.get(resolution) !== false;
        label.append(input, resolution === 'Quelle' ? 'Ohne Auflösung' : resolution);
        filters.append(label);
      }
      filters.hidden = !available.size;
      apply();
    }

    filters.addEventListener('change', event => {
      const input = event.target;
      if (!input.matches('input[type="checkbox"]')) return;
      selection.set(input.value, input.checked);
      try {
        localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(selection)));
      } catch {
        // Der Filter bleibt auch ohne dauerhaften Browserspeicher bedienbar.
      }
      apply();
    });
    update();
    return update;
  }

  function initialiseIndex() {
    const regions = [...document.querySelectorAll('[data-live-content]')];
    if (!regions.length) return;
    const resolutionFilters = document.querySelector('[data-resolution-filters]');
    const updateResolutions = initialiseResolutionFilters(resolutionFilters);
    const protectedRegions = [...regions, resolutionFilters];
    const watched = new Set([...document.querySelectorAll('[data-run-feedback][data-running="true"]')]
      .map(node => node.dataset.runFeedback));
    let request = null;
    let timer;

    function loadPage() {
      // Rückkehr und Laufstatus verwenden auch bei gleichzeitig ausgelösten Ereignissen denselben Abruf.
      if (request) return request;
      request = (async () => {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        try {
          const response = await fetch(location.pathname + location.search, { cache: 'no-store', signal: controller.signal });
          if (!response.ok) throw new Error('Ansicht nicht verfügbar');
          const page = new DOMParser().parseFromString(await response.text(), 'text/html');
          if (page.querySelectorAll('[data-run-feedback]').length !== 2
              || ['feed', 'import'].some(kind => {
                const status = page.querySelector(`[data-run-feedback="${kind}"]`);
                return !status?.querySelector('[data-run-message]')
                  || !['true', 'false'].includes(status.dataset.running);
              })
              || !page.querySelector('.history-filters')
              || regions.some(region => !page.querySelector(`[data-live-content="${region.dataset.liveContent}"]`))) {
            throw new Error('Ansicht unvollständig');
          }
          return page;
        } finally {
          clearTimeout(timeout);
        }
      })().finally(() => { request = null; });
      return request;
    }

    function scheduleStatus(delay = 3000) {
      clearTimeout(timer);
      if (watched.size && !document.hidden) timer = setTimeout(updateStatus, delay);
    }

    function applyStatus(page, refreshed = false) {
      const remoteFeedback = [...page.querySelectorAll('[data-run-feedback]')];
      const busy = remoteFeedback.some(node => node.dataset.running === 'true');
      for (const button of document.querySelectorAll('[data-run-start]')) button.disabled = busy;
      if (refreshed) {
        watched.clear();
        document.querySelector('[data-results-available]').hidden = true;
      }
      for (const incoming of remoteFeedback) {
        const kind = incoming.dataset.runFeedback;
        if (incoming.dataset.running === 'true') watched.add(kind);
        if (!watched.has(kind)) continue;
        const current = document.querySelector(`[data-run-feedback="${kind}"]`);
        current.hidden = false;
        current.dataset.running = incoming.dataset.running;
        const message = current.querySelector('[data-run-message]');
        const text = incoming.dataset.running === 'true'
          ? incoming.querySelector('[data-run-message]').textContent
          : 'Der Lauf ist beendet. Lade die neuen Ergebnisse mit «Ansicht aktualisieren».';
        if (message.textContent !== text) message.textContent = text;
        if (incoming.dataset.running === 'false') {
          document.querySelector('[data-results-available]').hidden = false;
        }
      }
      if (busy) scheduleStatus();
      else clearTimeout(timer);
    }

    async function updateStatus() {
      if (document.hidden) return;
      try {
        const page = await loadPage();
        // Tabellen und Filter bleiben erhalten, damit laufende Prüfungen
        // die aktuelle Bedienung nicht durch neue Ergebnisse unterbrechen.
        applyStatus(page);
      } catch {
        for (const kind of watched) {
          const message = document.querySelector(`[data-run-feedback="${kind}"] [data-run-message]`);
          const text = 'Der Laufstatus konnte nicht geladen werden. Prüfe den aktuellen Stand mit «Ansicht aktualisieren».';
          if (message.textContent !== text) message.textContent = text;
        }
        scheduleStatus(5000);
      }
    }

    refreshOnReturn(async () => {
      if (!canReplace(protectedRegions)) return false;
      const page = await loadPage();
      const filters = document.querySelector('.history-filters');
      const incomingFilters = page.querySelector('.history-filters');
      if (!canReplace(incomingFilters.hidden ? [...protectedRegions, filters] : protectedRegions)) return false;
      preservePosition(() => {
        for (const region of regions) {
          const incoming = page.querySelector(`[data-live-content="${region.dataset.liveContent}"]`);
          region.replaceChildren(...incoming.childNodes);
        }
        filters.hidden = incomingFilters.hidden;
        updateResolutions();
        applyStatus(page, true);
      });
      return true;
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) clearTimeout(timer);
      else scheduleStatus(0);
    });
    scheduleStatus();
  }

  initialiseLog();
  initialiseIndex();
})();
