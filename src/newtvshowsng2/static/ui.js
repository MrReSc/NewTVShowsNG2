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
