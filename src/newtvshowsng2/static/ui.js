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

      // Nur Statusfelder werden ersetzt. Tabellen, Filter und der Bedienpunkt
      // bleiben bis zum ausdrücklich angeforderten Laden neuer Ergebnisse erhalten.
      for (const current of document.querySelectorAll("[data-live-status]")) {
        const incoming = page.querySelector(`[data-live-status="${current.dataset.liveStatus}"]`);
        if (incoming && current.innerHTML !== incoming.innerHTML) {
          current.replaceChildren(...[...incoming.childNodes].map(node => node.cloneNode(true)));
        }
      }
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
