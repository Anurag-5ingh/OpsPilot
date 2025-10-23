(function(){
  window.Core = window.Core || {};
  const levels = ['debug','info','warn','error'];
  const Logger = levels.reduce((acc, lvl) => {
    acc[lvl] = (...args) => console[lvl](`[Core:${lvl}]`, ...args);
    return acc;
  }, {});
  window.Core.logger = Logger;
})();
