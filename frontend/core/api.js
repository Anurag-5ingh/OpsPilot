(function(){
  window.Core = window.Core || {};
  const JSON_HEADERS = { 'Content-Type': 'application/json' };
  async function request(url, options={}){
    const res = await fetch(url, options);
    const ct = res.headers.get('content-type')||'';
    const body = ct.includes('application/json') ? await res.json() : await res.text();
    if(!res.ok){ throw { status: res.status, body }; }
    return body;
  }
  const get = (url) => request(url);
  const post = (url, data) => request(url, { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(data) });
  window.Core.api = { get, post };
})();
