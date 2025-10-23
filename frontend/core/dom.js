(function(){
  window.Core = window.Core || {};
  const qs = (sel, root=document) => root.querySelector(sel);
  const qsa = (sel, root=document) => Array.from(root.querySelectorAll(sel));
  const show = (el) => el && el.classList && el.classList.remove('hidden');
  const hide = (el) => el && el.classList && el.classList.add('hidden');
  const toggle = (el, cond) => el && el.classList && el.classList.toggle('hidden', !!cond);
  function toast(message, type='info', duration=3500, containerId='toast-container') {
    try {
      const container = document.getElementById(containerId);
      if (!container) return;
      if (type === 'error') container.innerHTML = '';
      const el = document.createElement('div');
      el.className = `toast ${type}`;
      el.textContent = message;
      container.appendChild(el);
      setTimeout(() => el.remove(), duration);
    } catch (_) {}
  }
  window.Core.dom = { qs, qsa, show, hide, toggle, toast };
})();
