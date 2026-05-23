const Store = (() => {
  const _tables = new Map();
  let _index = null;

  return {
    setIndex(data) { _index = data; },
    getIndex() { return _index; },
    setTable(slug, data) { _tables.set(slug, data); },
    getTable(slug) { return _tables.get(slug) || null; },
  };
})();
