function createVirtualList({ container, items, renderBatch, batchSize = 50 }) {
  let rendered = 0;
  let observer = null;

  function renderNext() {
    const batch = items.slice(rendered, rendered + batchSize);
    if (!batch.length) {
      if (observer) { observer.disconnect(); observer = null; }
      const sentinel = container.querySelector('.load-more-sentinel');
      if (sentinel) sentinel.remove();
      return;
    }
    renderBatch(batch, rendered);
    rendered += batch.length;

    let sentinel = container.querySelector('.load-more-sentinel');
    if (!sentinel) {
      sentinel = document.createElement('div');
      sentinel.className = 'load-more-sentinel';
      container.appendChild(sentinel);
    } else {
      container.appendChild(sentinel);
    }

    if (rendered >= items.length) {
      if (observer) { observer.disconnect(); observer = null; }
      sentinel.remove();
    }
  }

  function init() {
    rendered = 0;
    renderNext();

    if (rendered < items.length) {
      observer = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting) renderNext();
      }, { rootMargin: '200px' });

      const sentinel = container.querySelector('.load-more-sentinel');
      if (sentinel) observer.observe(sentinel);
    }
  }

  function destroy() {
    if (observer) { observer.disconnect(); observer = null; }
  }

  return { init, destroy };
}
