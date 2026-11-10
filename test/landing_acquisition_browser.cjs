const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const repo = process.env.ACQUISITION_REPO || path.resolve(__dirname,'..');
const {JSDOM} = require(path.join(repo,'web/node_modules/jsdom'));
const site = fs.existsSync(path.join(__dirname,'acquisition.html')) ? __dirname : path.join(repo,'new site for swipies');
const code = name => fs.readFileSync(path.join(site,name),'utf8');
function tracker(query='', consent=false) {
  const dom = new JSDOM('<script data-landing="sales"></script><a id="cta" data-swipies-platform href="https://api.swipies.app/login">Start</a><a id="other" href="/help">Help</a>',{url:'https://sales.swipies.app/' + query,runScripts:'outside-only'});
  const w=dom.window;
  Object.defineProperty(w.document,'currentScript',{value:w.document.querySelector('script')});
  if(consent)w.localStorage.setItem('swipies_cookie_consent','accepted');
  return {dom,w};
}
test('UTM and campaign survive handoff; unrelated links remain unchanged',()=>{
  const {w}=tracker('?sw_campaign=abc&utm_source=telegram&utm_campaign=' + encodeURIComponent('Продажи & рост'));
  w.eval(code('acquisition-link.js'));
  const url=new URL(w.document.getElementById('cta').href);
  assert.equal(url.origin,'https://swipies.app');assert.equal(url.pathname,'/api/acquisition/go/sales');
  assert.equal(url.searchParams.get('utm_campaign'),'Продажи & рост');assert.equal(url.searchParams.get('sw_campaign'),'abc');
  assert.equal(w.document.getElementById('other').getAttribute('href'),'/help');
  assert.equal(w.sessionStorage.length,0);w.close();
});
test('attribution persists only with accepted analytics consent',()=>{
  const {w}=tracker('?utm_source=telegram',true);w.eval(code('acquisition-link.js'));
  assert.equal(JSON.parse(w.sessionStorage.getItem('swipies_acquisition_sales')).utm_source,'telegram');w.close();
  const refused=tracker().w;refused.sessionStorage.setItem('swipies_acquisition_sales','{"utm_source":"old"}');
  refused.eval(code('acquisition-link.js'));assert.equal(refused.sessionStorage.length,0);refused.close();
});
test('dynamic and middle-click buttons receive handoff; malformed storage is harmless',()=>{
  const {w}=tracker('',true);w.sessionStorage.setItem('swipies_acquisition_sales','null');w.eval(code('acquisition-link.js'));
  const a=w.document.createElement('a');a.setAttribute('data-swipies-platform','');a.href='https://api.swipies.app/login';w.document.body.append(a);
  a.dispatchEvent(new w.MouseEvent('auxclick',{bubbles:true,button:1}));
  assert.equal(new URL(a.href).pathname,'/api/acquisition/go/sales');w.close();
});
test('admin renders account and campaign text without executing HTML',async()=>{
  const dom=new JSDOM(code('acquisition.html'),{url:'https://swipies.app/admin/acquisition',runScripts:'outside-only'}),w=dom.window;
  const evil='<img src=x onerror="alert(1)">';let called=false;w.alert=()=>called=true;
  w.localStorage.setItem('swipies_admin_token','test-admin');
  const fixtures={landings:[{slug:'sales',name:'Sales',url:'https://sales.swipies.app/',active:1}],campaigns:[{id:'c1',name:evil,landing:'sales',active:1,utm_source:'telegram',utm_medium:'paid',utm_campaign:'Launch',url:'https://sales.swipies.app/?utm_source=telegram'}],report:{rows:[{created_at:new Date().toISOString(),landing:'sales',accounts:[{email:evil,nickname:'User'}],utm_source:'telegram',utm_medium:'paid',utm_campaign:'Launch'}],total:1,summary:[{landing:'sales',transitions:1}],accounts_status:'ready'}};
  w.fetch=async(url,options)=>{
    assert.equal(options.headers.Authorization,'Bearer test-admin');
    return {ok:true,status:200,json:async()=>({code:0,data:fixtures[url.split('/').pop().split('?')[0]]})};
  };
  w.eval(code('acquisition-admin.js'));
  for(let i=0;i<12;i++)await new Promise(r=>setImmediate(r));
  assert.match(w.document.getElementById('transitions').textContent,/<img/);
  assert.equal(w.document.querySelectorAll('img').length,0);assert.equal(called,false);
  assert.equal(w.document.getElementById('next').disabled,true);
  assert.match(w.document.getElementById('snippet').textContent,/data-landing="sales"/);w.close();
});
