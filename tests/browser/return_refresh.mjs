import assert from 'node:assert/strict';
import fs from 'node:fs';

const [baseUrl = 'http://127.0.0.1:28733', browserUrl = 'ws://127.0.0.1:9334/session', outputDirectory = 'out/ui-return-check'] = process.argv.slice(2);
fs.mkdirSync(outputDirectory, { recursive: true });
const ws = new WebSocket(browserUrl);
const pending = new Map();
let serial = 0;
ws.onmessage = event => {
  const message = JSON.parse(event.data);
  if (!pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.type === 'error') reject(new Error(JSON.stringify(message)));
  else resolve(message.result);
};
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
function call(method, params) {
  return new Promise((resolve, reject) => {
    const id = ++serial;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
await call('session.new', { capabilities: {} });
const { context } = await call('browsingContext.create', { type: 'tab' });
const { context: other } = await call('browsingContext.create', { type: 'tab' });
async function run(expression) {
  const result = await call('script.evaluate', { expression: `(async () => JSON.stringify(await (async () => { ${expression} })()))()`, target: { context }, awaitPromise: true });
  if (result.type === 'exception') throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value === undefined ? undefined : JSON.parse(result.result.value);
}
async function waitFor(condition) {
  await run(`await new Promise((resolve, reject) => {
    const start = performance.now();
    const check = () => {
      if (${condition}) resolve();
      else if (performance.now() - start > 15000) reject(new Error('Timeout: ' + ${JSON.stringify(condition)}));
      else setTimeout(check, 25);
    }; check();
  }); return true;`);
}
async function open(path = '/#overview', width = 1440) {
  await call('browsingContext.activate', { context });
  await call('browsingContext.setViewport', { context, viewport: { width, height: 700 } });
  await call('browsingContext.navigate', { context, url: 'about:blank', wait: 'complete' });
  await call('browsingContext.navigate', { context, url: baseUrl + path, wait: 'complete' });
  await run(`
    window.__clock = 0;
    const realNow = Date.now;
    Date.now = () => realNow() + window.__clock;
    window.__fixture = await (await fetch(location.href)).text();
    window.__requests = [];
    window.__mode = 'ok';
    window.__delay = 0;
    window.fetch = async (url, options) => {
      __requests.push({url: String(url), cache: options?.cache});
      const mode = __mode;
      const delay = mode === 'timeout' ? 15000 : __delay;
      if (delay) await new Promise((resolve, reject) => {
        const timer = setTimeout(resolve, delay);
        options?.signal?.addEventListener('abort', () => {
          clearTimeout(timer);
          reject(new DOMException('Simulierte Zeitüberschreitung', 'AbortError'));
        }, { once: true });
      });
      if (mode === 'offline') throw new TypeError('Simulierter Verbindungsfehler');
      if (mode === 'unavailable') return new Response('', {status: 503});
      if (mode === 'incomplete') return new Response('<html><body>Unvollständig</body></html>');
      if (mode === 'incomplete-status') {
        const page = new DOMParser().parseFromString(__fixture, 'text/html');
        page.querySelector('[data-run-message]').remove();
        return new Response(page.documentElement.outerHTML);
      }
      return new Response(__fixture, {headers: {'Content-Type': 'text/html'}});
    };
    return true;
  `);
}
async function returnToTab(stale = true) {
  await call('browsingContext.activate', { context: other });
  assert.equal(await run('return document.hidden;'), true, 'Der Tab ist tatsächlich unsichtbar');
  if (stale) await run('window.__clock += 61000; return true;');
  await call('browsingContext.activate', { context });
  await run('await new Promise(resolve => setTimeout(resolve, 100)); return true;');
}
async function fixture(change) {
  await run(`const page = new DOMParser().parseFromString(__fixture, 'text/html'); ${change}; window.__fixture = page.documentElement.outerHTML; return true;`);
}
async function screenshot(name) {
  const image = await call('browsingContext.captureScreenshot', { context, origin: 'viewport' });
  fs.writeFileSync(`${outputDirectory}/${name}.png`, Buffer.from(image.data, 'base64'));
}
let passed = 0;
async function test(name, body) {
  await body();
  passed++;
  console.log(`PASS ${name}`);
}

try {
  await test('Keine Aktualisierung bei kurzer Abwesenheit oder allein durch Zeitablauf', async () => {
    await open();
    await returnToTab(false);
    assert.equal(await run('return __requests.length;'), 0);
    await run('__clock += 61000; await new Promise(resolve => setTimeout(resolve, 100)); return true;');
    assert.equal(await run('return __requests.length;'), 0);
  });

  await test('Neue Inhalte und Erzeugungszeitpunkt bei Rückkehr, nur ein Abruf', async () => {
    await open();
    await fixture(`page.querySelector('#overview-view .inventory .cell-content').textContent = '7 / 10 vorhanden'; page.querySelector('footer').textContent = 'Erzeugt am aktualisierten Beispielzeitpunkt'`);
    await returnToTab();
    await waitFor(`document.querySelector('#overview-view .inventory .cell-content').textContent === '7 / 10 vorhanden'`);
    assert.equal(await run('return __requests.length;'), 1);
    assert.equal(await run('return __requests[0].cache;'), 'no-store');
    assert.match(await run('return document.querySelector("footer").textContent;'), /aktualisierten/);
    await returnToTab(false);
    assert.equal(await run('return __requests.length;'), 1);
    await screenshot('overview-desktop');
  });

  await test('Historienfilter, Ansicht und sichtbare Zeile bleiben erhalten', async () => {
    await open('/#history');
    const before = await run(`
      document.querySelector('#history-filter-import').click();
      window.scrollTo(0, 400);
      const row = document.querySelectorAll('#history-view tbody tr')[2];
      window.__anchorKey = row.dataset.rowKey;
      return {top: row.getBoundingClientRect().top, y: scrollY};
    `);
    assert.ok(before.y > 0);
    await fixture(`const body = page.querySelector('#history-view tbody'); const row = body.firstElementChild.cloneNode(true); row.dataset.rowKey = 'zusatzzeile'; body.prepend(row)`);
    await returnToTab();
    await waitFor(`document.querySelector('#history-view [data-row-key="zusatzzeile"]')`);
    const after = await run(`return {hash: location.hash, checked: document.querySelector('#history-filter-import').checked, top: [...document.querySelectorAll('#history-view tbody tr')].find(row => row.dataset.rowKey === __anchorKey).getBoundingClientRect().top};`);
    assert.equal(after.hash, '#history');
    assert.equal(after.checked, false);
    assert.ok(Math.abs(after.top - before.top) < 1, JSON.stringify({before, after}));
    await screenshot('history-desktop');
  });

  await test('Fokussierte Tabellenaktion verschiebt die Aktualisierung bis zum Verlassen', async () => {
    await open();
    await run(`document.querySelector('.complete-action button').focus(); return true;`);
    await fixture(`page.querySelector('#overview-view .inventory .cell-content').textContent = 'Fokusprüfung abgeschlossen'`);
    await returnToTab();
    assert.equal(await run('return __requests.length;'), 0);
    assert.equal(await run(`return document.activeElement.matches('.complete-action button');`), true);
    await run('document.activeElement.blur(); return true;');
    await waitFor(`document.querySelector('#overview-view .inventory .cell-content').textContent === 'Fokusprüfung abgeschlossen'`);
    assert.equal(await run('return __requests.length;'), 1);
  });

  await test('Textauswahl bleibt bis zu ihrem Aufheben erhalten', async () => {
    await open();
    await run(`const range = document.createRange(); range.selectNodeContents(document.querySelector('#overview-view .release-title')); const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range); return true;`);
    const selected = await run('return getSelection().toString();');
    await fixture(`page.querySelector('#overview-view .inventory .cell-content').textContent = 'Auswahlprüfung abgeschlossen'`);
    await returnToTab();
    assert.equal(await run('return __requests.length;'), 0);
    assert.equal(await run('return getSelection().toString();'), selected);
    await run('getSelection().removeAllRanges(); return true;');
    await waitFor(`document.querySelector('#overview-view .inventory .cell-content').textContent === 'Auswahlprüfung abgeschlossen'`);
  });

  for (const mode of ['offline', 'unavailable', 'incomplete', 'incomplete-status', 'timeout']) {
    await test(`Fehler ${mode}: Inhalte bleiben sichtbar, Wiederholung lädt neue Ergebnisse`, async () => {
      await open();
      const original = await run('return document.querySelector("#overview-view .panel").innerHTML;');
      await fixture(`page.querySelector('#overview-view .inventory .cell-content').textContent = 'Diese unvollständige Antwort darf nicht übernommen werden'`);
      await run(`window.__mode = ${JSON.stringify(mode)}; return true;`);
      await returnToTab();
      await waitFor(`!document.querySelector('[data-return-feedback]').hidden`);
      assert.equal(await run('return document.querySelector("#overview-view .panel").innerHTML;'), original);
      assert.equal(await run('return location.hash;'), '#overview');
      if (mode === 'offline') await screenshot('error-desktop');
      await fixture(`page.querySelector('#overview-view .inventory .cell-content').textContent = 'Wiederholung erfolgreich'`);
      await run(`window.__mode = 'ok'; document.querySelector('[data-return-feedback] button').click(); return true;`);
      await waitFor(`document.querySelector('#overview-view .inventory .cell-content').textContent === 'Wiederholung erfolgreich'`);
      assert.equal(await run(`return document.querySelector('[data-return-feedback]').hidden;`), true);
    });
  }

  await test('Leere Historie kann gefüllt und wieder geleert werden', async () => {
    await open('/?state=empty#history');
    assert.equal(await run('return document.querySelector(".history-filters").hidden;'), true);
    const response = await fetch(baseUrl + '/');
    const html = await response.text();
    await run(`__fixture = ${JSON.stringify(html)}; __requests = []; return true;`);
    await returnToTab();
    await waitFor('!document.querySelector(".history-filters").hidden');
    assert.ok(await run('return document.querySelectorAll("#history-view tbody tr").length;') > 0);
    await fixture(`page.querySelector('[data-live-content="history"]').innerHTML = '<div class="empty">Keine Einträge</div>'; page.querySelector('.history-filters').hidden = true`);
    await returnToTab();
    await waitFor('document.querySelector(".history-filters").hidden');
    assert.equal(await run('return document.querySelectorAll("#history-view tbody tr").length;'), 0);
  });

  await test('Rückkehr und laufende Statusabfrage teilen dieselbe Anfrage', async () => {
    await open('/?state=running#media-import');
    await run('__delay = 3300; return true;');
    await fixture(`for (const node of page.querySelectorAll('[data-run-feedback]')) { node.dataset.running = 'false'; node.hidden = true; } for (const button of page.querySelectorAll('[data-run-start]')) button.disabled = false; page.querySelector('footer').textContent = 'Beide Läufe abgeschlossen'`);
    await returnToTab();
    await waitFor('document.querySelector("footer").textContent === "Beide Läufe abgeschlossen"');
    assert.equal(await run('return __requests.length;'), 1);
    assert.equal(await run('return [...document.querySelectorAll("[data-run-start]")].every(button => !button.disabled);'), true);
    assert.equal(await run('return document.querySelector("[data-results-available]").hidden;'), true);
  });

  await test('Schnelle Antwort bei laufendem Vorgang erzeugt keinen doppelten Rückkehrabruf', async () => {
    await open('/?state=running#overview');
    await returnToTab();
    await waitFor('__requests.length >= 1');
    assert.equal(await run('return __requests.length;'), 1);
  });

  await test('Statusabfragen pausieren im unsichtbaren Tab', async () => {
    await open('/?state=running#overview');
    await call('browsingContext.activate', { context: other });
    await run('await new Promise(resolve => setTimeout(resolve, 3200)); return true;');
    assert.equal(await run('return __requests.length;'), 0);
    await call('browsingContext.activate', { context });
    await waitFor('__requests.length >= 1');
  });

  await test('Log erhält Filter, Ergebnisseite, Fokus und Textauswahl im Suchfeld', async () => {
    await open('/log?period=7d&level=DEBUG&page=2&q=Beispiel');
    await run(`const search = document.querySelector('[name="q"]'); search.focus(); search.setSelectionRange(1, 5); return true;`);
    await fixture(`page.querySelector('.message').textContent = 'Beispiel: Neue Logergebnisse'`);
    await returnToTab();
    await waitFor(`document.querySelector('.message').textContent === 'Beispiel: Neue Logergebnisse'`);
    const actual = await run(`const search = document.querySelector('[name="q"]'); return {url: __requests[0].url, active: document.activeElement === search, value: search.value, start: search.selectionStart, end: search.selectionEnd, count: __requests.length};`);
    assert.equal(actual.count, 1);
    assert.equal(actual.active, true);
    assert.equal(actual.value, 'Beispiel');
    assert.equal(actual.start, 1);
    assert.equal(actual.end, 5);
    assert.match(actual.url, /page=2/);
    assert.match(actual.url, /period=7d/);
    await screenshot('log-desktop');
  });

  await test('Logfilterwechsel verwirft einen noch laufenden automatischen Abruf', async () => {
    await open('/log');
    await run('__delay = 500; return true;');
    await returnToTab();
    await run(`document.querySelector('[name="level"]').value = 'ERROR'; document.querySelector('[name="level"]').dispatchEvent(new Event('change')); return true;`);
    await waitFor(`new URL(location.href).searchParams.get('level') === 'ERROR'`);
    assert.equal(await run('return document.querySelector("[data-return-feedback]").hidden;'), true);
    assert.equal(await run('return __requests.length;'), 2);
  });

  await test('Wiederherstellung aus dem Navigationscache und Fensterfokus', async () => {
    await open();
    await fixture(`page.querySelector('footer').textContent = 'Navigationscache aktualisiert'`);
    await run(`__clock += 61000; dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true})); return true;`);
    await waitFor('document.querySelector("footer").textContent === "Navigationscache aktualisiert"');
    await fixture(`page.querySelector('footer').textContent = 'Fensterfokus aktualisiert'`);
    await run(`__clock += 61000; dispatchEvent(new Event('focus')); return true;`);
    await waitFor('document.querySelector("footer").textContent === "Fensterfokus aktualisiert"');
    assert.equal(await run('return __requests.length;'), 2);
  });

  await test('Mobile Ansicht aktualisiert ohne horizontalen Überlauf', async () => {
    await open('/#media-import', 390);
    await fixture(`page.querySelector('#media-import-view .import-details > span').textContent = 'Beispiel: Importstatus aktualisiert'`);
    await returnToTab();
    await waitFor(`document.querySelector('#media-import-view .import-details > span').textContent === 'Beispiel: Importstatus aktualisiert'`);
    assert.equal(await run('return document.documentElement.scrollWidth <= innerWidth;'), true);
    await screenshot('import-mobile');
    await run(`__mode = 'offline'; return true;`);
    await returnToTab();
    await waitFor('!document.querySelector("[data-return-feedback]").hidden');
    assert.equal(await run('return document.documentElement.scrollWidth <= innerWidth;'), true);
    await screenshot('error-mobile');
  });

  await test('Auflösungsfilter zeigen vorhandene Werte einmalig neben dem Feed-Abgleich', async () => {
    await open();
    await run(`localStorage.removeItem('newtvshowsng2.feed.resolutions'); return true;`);
    await open();
    const actual = await run(`
      const filters = document.querySelector('[data-resolution-filters]');
      const button = document.querySelector('[action="/run/feed"] button');
      return {
        values: [...filters.querySelectorAll('input')].map(input => input.value),
        checked: [...filters.querySelectorAll('input')].every(input => input.checked),
        beside: filters.getBoundingClientRect().left > button.getBoundingClientRect().right
          && Math.abs(filters.getBoundingClientRect().top - button.getBoundingClientRect().top) < 1
      };
    `);
    assert.deepEqual(actual.values, ['720p', '1080p', '2160p']);
    assert.equal(actual.checked, true);
    assert.equal(actual.beside, true);
  });

  await test('Auflösungswahl filtert nur Links und bleibt nach dem Neuladen erhalten', async () => {
    const before = await run(`return [...document.querySelectorAll('#overview-view tbody tr')].map(row => ({key: row.dataset.rowKey, form: row.querySelector('form')?.outerHTML}));`);
    await run(`for (const input of document.querySelectorAll('[data-resolution-filters] input')) if (input.value !== '1080p') input.click(); return true;`);
    await open();
    const actual = await run(`return {
      values: [...document.querySelectorAll('[data-resolution-filters] input:checked')].map(input => input.value),
      resolutions: [...new Set([...document.querySelectorAll('#overview-view [data-resolution]:not([hidden])')].map(link => link.dataset.resolution))],
      rows: [...document.querySelectorAll('#overview-view tbody tr')].map(row => ({key: row.dataset.rowKey, form: row.querySelector('form')?.outerHTML}))
    };`);
    assert.deepEqual(actual.values, ['1080p']);
    assert.deepEqual(actual.resolutions, ['1080p']);
    assert.deepEqual(actual.rows, before);
    await screenshot('resolution-filter-desktop');
    await call('browsingContext.setViewport', { context, viewport: { width: 390, height: 700 } });
    assert.equal(await run('return document.documentElement.scrollWidth <= innerWidth;'), true);
    await screenshot('resolution-filter-mobile');
    await run(`document.querySelector('[data-resolution-filters] input:checked').click(); return true;`);
    await open();
    assert.equal(await run(`return document.querySelectorAll('#overview-view [data-resolution]:not([hidden])').length;`), 0);
    assert.equal(await run(`return [...document.querySelectorAll('#overview-view .resolution-empty')].every(node => !node.hidden);`), true);
  });

  await test('Neue Auflösungen und unbekannte Quellen ergänzen die Filter bei Rückkehr', async () => {
    await fixture(`
      for (const link of page.querySelectorAll('#overview-view [data-resolution="720p"]')) link.remove();
      const group = page.querySelector('#overview-view .variant-links');
      for (const [resolution, rank] of [['576p', '576'], ['Quelle', '10000']]) {
        const link = group.querySelector('a').cloneNode(true);
        link.dataset.resolution = resolution;
        link.dataset.resolutionRank = rank;
        link.textContent = resolution;
        group.append(link);
      }
    `);
    await returnToTab();
    await waitFor(`document.querySelector('[data-resolution-filters] input[value="576p"]')`);
    assert.deepEqual(await run(`return [...document.querySelectorAll('[data-resolution-filters] input')].map(input => [input.value, input.checked]);`), [
      ['576p', true], ['1080p', false], ['2160p', false], ['Quelle', true],
    ]);
    assert.equal(await run(`return document.querySelector('[data-resolution-filters] input[value="Quelle"]').parentElement.textContent;`), 'Ohne Auflösung');
    await run(`document.querySelector('[data-resolution-filters] input[value="Quelle"]').click(); document.activeElement.blur(); return true;`);
    assert.equal(await run(`return document.querySelector('#overview-view [data-resolution="Quelle"]').hidden;`), true);
    await fixture(`page.querySelector('footer').textContent = 'Auflösungen erneut geladen'`);
    await returnToTab();
    await waitFor(`document.querySelector('footer').textContent === 'Auflösungen erneut geladen'`);
    assert.equal(await run(`return document.querySelector('#overview-view [data-resolution="Quelle"]').hidden;`), true);
    await open();
    assert.equal(await run(`return document.querySelector('[data-resolution-filters] input[value="720p"]').checked;`), false);
  });

  await test('Leerer Feed blendet die Auflösungsfilter aus und ungültiger Speicher blockiert sie nicht', async () => {
    await open('/?state=empty#overview');
    assert.equal(await run(`return document.querySelector('[data-resolution-filters]').hidden;`), true);
    await run(`localStorage.setItem('newtvshowsng2.feed.resolutions', '{ungültig'); return true;`);
    await open();
    assert.equal(await run(`return [...document.querySelectorAll('[data-resolution-filters] input')].every(input => input.checked);`), true);
    await run(`
      Storage.prototype.setItem = () => { throw new DOMException('Browserspeicher gesperrt', 'SecurityError'); };
      document.querySelector('[data-resolution-filters] input[value="1080p"]').click();
      return true;
    `);
    assert.equal(await run(`return [...document.querySelectorAll('#overview-view [data-resolution="1080p"]')].every(link => link.hidden);`), true);
    await run(`localStorage.removeItem('newtvshowsng2.feed.resolutions'); return true;`);
  });

  console.log(`${passed} Browserprüfungen erfolgreich`);
} finally {
  await call('browsingContext.close', { context });
  await call('browsingContext.close', { context: other });
  await call('session.end', {});
  ws.close();
}
