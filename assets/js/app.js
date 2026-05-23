// ── Bootstrap ──────────────────────────────────────────────────────────────
(async function init() {
  try {
    const res = await fetch('data/index.json');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const index = await res.json();
    Store.setIndex(index);
  } catch (e) {
    console.error('Failed to load index.json:', e);
  }

  // Register routes
  Router.on('', () => {
Renderer.renderHome();
  });

  Router.on('table/:slug', async ({ slug }) => {
await loadAndRenderTable(slug, null);
  });

  Router.on('table/:slug/field/:fieldNo', async ({ slug, fieldNo }) => {
await loadAndRenderTable(slug, parseInt(fieldNo, 10));
  });

  Router.start();
})();

// ── Helpers ────────────────────────────────────────────────────────────────

async function loadAndRenderTable(slug, highlightFieldNo) {
  let table = Store.getTable(slug);
  if (!table) {
    Renderer.renderLoading();
    try {
      const res = await fetch(`data/tables/${slug}.json`);
      if (!res.ok) throw new Error('Table not found');
      table = await res.json();
      Store.setTable(slug, table);
    } catch (e) {
      Renderer.renderError(`Could not load table "${slug}".`);
      return;
    }
  }
  Renderer.renderTableDetail(table, highlightFieldNo);
}

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
