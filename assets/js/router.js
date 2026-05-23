const Router = (() => {
  const routes = [];

  function parse(hash) {
    const raw = hash.replace(/^#\/?/, '');
    const [pathPart, queryPart] = raw.split('?');
    const segments = pathPart ? pathPart.split('/') : [];
    const params = {};
    if (queryPart) {
      queryPart.split('&').forEach(pair => {
        const [k, v] = pair.split('=');
        if (k) params[decodeURIComponent(k)] = decodeURIComponent(v || '');
      });
    }
    return { segments, params };
  }

  function match(segments) {
    for (const route of routes) {
      const parts = route.pattern.split('/').filter(Boolean);
      if (parts.length !== segments.length && !route.pattern.endsWith('*')) continue;
      const extracted = {};
      let matched = true;
      for (let i = 0; i < parts.length; i++) {
        if (parts[i].startsWith(':')) {
          extracted[parts[i].slice(1)] = segments[i];
        } else if (parts[i] !== segments[i]) {
          matched = false;
          break;
        }
      }
      if (matched) return { handler: route.handler, params: extracted };
    }
    return null;
  }

  function dispatch() {
    const { segments, params: queryParams } = parse(location.hash);
    const result = match(segments);
    if (result) {
      result.handler({ ...result.params, ...queryParams });
    }
  }

  return {
    on(pattern, handler) {
      routes.push({ pattern, handler });
    },
    navigate(hash) {
      location.hash = hash;
    },
    start() {
      window.addEventListener('hashchange', dispatch);
      dispatch();
    },
    dispatch,
  };
})();
