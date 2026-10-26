/* One scroll owner for the stable transcript. No user text or external code. */
(() => {
  if (window.ipedsTranscriptScroll) return;
  let element = null, resize = null, frame = 0, request = -1;
  let following = true, editing = false, dragging = false, touchY = null;
  const bottom = () => element && element.scrollHeight - element.clientHeight - element.scrollTop < 48;
  const schedule = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      if (element?.isConnected && following && !editing) {
        // Instant positioning before paint avoids a top-to-bottom animation.
        element.scrollTop = element.scrollHeight;
      }
    });
  };
  const scroll = () => {
    if (bottom()) following = true;
    else if (dragging) following = false;
  };
  const wheel = event => { if (event.deltaY < 0) following = false; };
  const pointer = event => {
    const rect = element.getBoundingClientRect();
    dragging = event.clientX >= rect.right - 20;
  };
  const release = () => { dragging = false; };
  const touchStart = event => { touchY = event.touches[0]?.clientY ?? null; };
  const touchMove = event => {
    const y = event.touches[0]?.clientY;
    if (touchY !== null && y > touchY) following = false;
    touchY = y ?? null;
  };
  const key = event => {
    if (event.target === element && ['PageUp', 'Home', 'ArrowUp'].includes(event.key)) following = false;
  };
  const bindings = {scroll, wheel, pointerdown:pointer, touchstart:touchStart, touchmove:touchMove, keydown:key};
  const bind = () => {
    const next = document.querySelector('.st-key-conversation_messages');
    if (next === element) return;
    if (element) for (const [name, fn] of Object.entries(bindings)) element.removeEventListener(name, fn);
    resize?.disconnect();
    element = next;
    if (!element) return;
    for (const [name, fn] of Object.entries(bindings)) element.addEventListener(name, fn, {passive:true});
    resize = new ResizeObserver(schedule);
    resize.observe(element);
    if (element.firstElementChild) resize.observe(element.firstElementChild);
    schedule();
  };
  // Includes late chart/table layout and Streamlit's pending-to-answer replacement.
  const observer = new MutationObserver(() => { bind(); schedule(); });
  observer.observe(document.body, {childList:true, subtree:true, characterData:true});
  window.addEventListener('pointerup', release, {passive:true});
  window.ipedsTranscriptScroll = {
    update(config) {
      bind();
      if (config.request !== request) {
        request = config.request;
        following = true;
      }
      if (config.editing && !editing) following = false;
      editing = config.editing;
      schedule();
    }
  };
})();
