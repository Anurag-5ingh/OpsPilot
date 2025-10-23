(function(){
  window.Core = window.Core || {};
  const subs = {};
  function on(event, handler){ (subs[event] = subs[event] || []).push(handler); return () => off(event, handler); }
  function off(event, handler){ const arr = subs[event]||[]; const i = arr.indexOf(handler); if(i>-1) arr.splice(i,1); }
  function emit(event, data){ (subs[event]||[]).forEach(h => { try{ h(data); } catch(e){ console.error('Event handler error', e); } }); }
  window.Core.events = { on, off, emit };
})();
