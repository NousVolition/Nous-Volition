(() => {
  // The regions retain native touch scrolling and keyboard scrolling. Hints
  // appear only when there really are columns outside the visible area.
  for (const region of document.querySelectorAll('.sims-table-scroll')) {
    const hint = document.getElementById(region.getAttribute('aria-describedby'));
    const update = () => {
      const overflow = region.scrollWidth > region.clientWidth + 1;
      hint.hidden = !overflow;
      region.tabIndex = overflow ? 0 : -1;
    };
    update();
    if (typeof ResizeObserver === 'function') {
      const observer = new ResizeObserver(update);
      observer.observe(region);
      observer.observe(region.querySelector('table'));
    } else {
      window.addEventListener('resize', update);
    }
  }
  // A number pad is more useful than a text keyboard for a trial seed.
  document.querySelectorAll('[data-control="seed"]').forEach(input => {
    input.setAttribute('inputmode', 'numeric');
  });
})();
