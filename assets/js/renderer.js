const Renderer = (() => {
  let _currentVirtualList = null;

  function mount(html) {
    const app = document.getElementById('app');
    if (_currentVirtualList) { _currentVirtualList.destroy(); _currentVirtualList = null; }
    app.innerHTML = html;
  }

  function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ── Home view ──────────────────────────────────────────────────────────────
  function renderHome() {
    const index = Store.getIndex();
    if (!index) { renderError('Could not load table index.'); return; }

    mount(`
      <div class="home-header">
        <h1>BC Tooltip Directory</h1>
        <p>Browse and search fields and tooltips for Business Central tables.</p>
      </div>
      <div class="table-list-wrap">
        <table class="table-list">
          <thead>
            <tr>
              <th>ID</th>
              <th>Table</th>
              <th style="text-align:right">Fields</th>
              <th style="text-align:center">Has empty</th>
            </tr>
            <tr class="table-list__filters">
              <th><input type="search" id="col-filter-id"     class="col-filter" placeholder="ID…"     autocomplete="off"></th>
              <th><input type="search" id="col-filter-name"   class="col-filter" placeholder="Name…"   autocomplete="off"></th>
              <th><input type="number" id="col-filter-fields" class="col-filter col-filter--num" placeholder="≥" min="0"></th>
              <th>
                <select id="col-filter-empty" class="col-filter col-filter--select">
                  <option value="">All</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </th>
            </tr>
          </thead>
          <tbody id="table-list-body"></tbody>
        </table>
        <div id="table-list-empty" class="table-list__no-results" style="display:none">No tables match the filters.</div>
      </div>
    `);

    const tbody      = document.getElementById('table-list-body');
    const emptyMsg   = document.getElementById('table-list-empty');
    const fId        = document.getElementById('col-filter-id');
    const fName      = document.getElementById('col-filter-name');
    const fFields    = document.getElementById('col-filter-fields');
    const fEmpty     = document.getElementById('col-filter-empty');

    function buildRows(tables) {
      return tables.map(t => `
        <tr>
          <td class="table-list__id">${t.id}</td>
          <td><a href="#/table/${t.slug}">${escHtml(t.name)}</a></td>
          <td class="table-list__fields">${t.fieldCount}</td>
          <td class="table-list__has-empty">${t.hasEmpty
            ? '<span class="badge badge--orange">yes</span>'
            : '<span class="badge badge--green">no</span>'}</td>
        </tr>`).join('');
    }

    function applyFilter() {
      const qId     = fId.value.trim();
      const qName   = fName.value.trim().toLowerCase();
      const qFields = fFields.value !== '' ? parseInt(fFields.value, 10) : null;
      const qEmpty  = fEmpty.value;

      const filtered = index.tables.filter(t => {
        if (qId     && !String(t.id).includes(qId))         return false;
        if (qName   && !t.name.toLowerCase().includes(qName)) return false;
        if (qFields !== null && t.fieldCount < qFields)      return false;
        if (qEmpty === 'yes' && !t.hasEmpty)                 return false;
        if (qEmpty === 'no'  &&  t.hasEmpty)                 return false;
        return true;
      });
      tbody.innerHTML = buildRows(filtered);
      emptyMsg.style.display = filtered.length ? 'none' : 'block';
    }

    tbody.innerHTML = buildRows(index.tables);
    [fId, fName, fFields, fEmpty].forEach(el => el.addEventListener('input', applyFilter));
  }

  // ── Table detail view ──────────────────────────────────────────────────────
  function renderTableDetail(table, highlightFieldNo) {
    const fields = table.fields || [];

    mount(`
      <div class="table-detail__header">
        <div class="table-detail__title-area">
          <div class="table-detail__breadcrumb"><a href="#/">Tables</a> / ${escHtml(table.name)}</div>
          <div class="table-detail__title">
            ${escHtml(table.name)}
            <span class="table-detail__id">Table ${table.id}</span>
          </div>
          ${table.description ? `<div class="table-detail__desc">${escHtml(table.description)}</div>` : ''}
        </div>
        <span class="table-detail__count">${fields.length} fields</span>
      </div>
      <div class="fields-table-wrap">
        <table class="fields-table">
          <thead>
            <tr>
              <th>No.</th>
              <th>Field Name</th>
              <th>Tooltip</th>
            </tr>
          </thead>
          <tbody id="fields-tbody"></tbody>
        </table>
      </div>
    `);

    const tbody = document.getElementById('fields-tbody');

    _currentVirtualList = createVirtualList({
      container: tbody,
      items: fields,
      batchSize: 60,
      renderBatch(batch) {
        const fragment = document.createDocumentFragment();
        for (const f of batch) {
          const tr = document.createElement('tr');
          if (highlightFieldNo && f.no === highlightFieldNo) tr.classList.add('highlighted');
          tr.id = `field-${f.no}`;
          tr.innerHTML = `
            <td class="field-no">${f.no}</td>
            <td class="field-name">${escHtml(f.name)}</td>
            <td class="field-tooltip">${escHtml(f.tooltip).replace(/\n/g, '<br>')}</td>
          `;
          fragment.appendChild(tr);
        }
        tbody.appendChild(fragment);

        if (highlightFieldNo) {
          const el = document.getElementById(`field-${highlightFieldNo}`);
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    });

    _currentVirtualList.init();
  }

  function renderLoading(msg = 'Loading…') {
    mount(`<div class="state-loading"><div class="state-loading__spinner"></div><span>${msg}</span></div>`);
  }

  function renderError(msg) {
    mount(`<div class="state-error"><div class="state-error__icon">⚠️</div><div class="state-error__title">Error</div><div class="state-error__desc">${escHtml(msg)}</div></div>`);
  }

  return { renderHome, renderTableDetail, renderLoading, renderError };
})();
