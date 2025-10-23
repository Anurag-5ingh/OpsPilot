(function(){
  window.Core = window.Core || {};
  const ns = 'ops';
  function k(key){ return `${ns}:${key}`; }
  function get(key, def=null){ try{ const v = localStorage.getItem(k(key)); return v? JSON.parse(v): def; } catch{ return def; } }
  function set(key, val){ try{ localStorage.setItem(k(key), JSON.stringify(val)); } catch(e){} }
  function del(key){ try{ localStorage.removeItem(k(key)); } catch(e){} }
  window.Core.storage = { get, set, del };
})();
