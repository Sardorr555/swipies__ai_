const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const site = process.argv[2] || path.resolve(__dirname, '../new site for swipies');
const source = fs.readFileSync(path.join(site, 'agent-setup.js'), 'utf8');
const context = {document: {getElementById: () => null}};
vm.createContext(context); vm.runInContext(source, context);
const build = context.buildSwipiesSetup;
const cases = [];
for (const client of ['codex','claude','cursor']) {
  for (const os of ['windows','posix']) {
    for (const interpreter of ['python','python3','py']) {
      const file = os === 'windows' ? "C:\\Users\\A's $(`test`)\\swipies_agent_client.py" : "/home/A's $(test) `test`/swipies_agent_client.py";
      const output = build(client,os,interpreter,file);
      assert.equal(typeof output,'string');
      if (client === 'cursor') {
        const config = JSON.parse(output).mcpServers.swipies;
        assert.equal(config.command,interpreter); assert.deepEqual(config.args,[file]);
      } else cases.push({client,os,interpreter,file,output});
    }
  }
}
for (const file of ['', 'relative/client.py', '/home/user/client.py.txt', '/home/user/client.py\n', '/home/user/\0client.py']) assert.equal(build('codex','posix','python',file),null);
assert.equal(build('codex','windows','python','/tmp/client.py'),null);
assert.equal(build('codex','posix','python;evil','/tmp/client.py'),null);
assert.equal(build('unknown','posix','python','/tmp/client.py'),null);
const textMatch = source.match(/const translations = ([\s\S]*?);\n  const byId/);
const translations = vm.runInNewContext('(' + textMatch[1] + ')');
const keys = Object.keys(translations.en).sort();
for (const lang of ['ru','uz']) assert.deepEqual(Object.keys(translations[lang]).sort(),keys);
const html = fs.readFileSync(path.join(site, 'agents.html'),'utf8');
for (const [,key] of html.matchAll(/data-setup-i18n="([^"]+)"/g)) for (const lang of ['en','ru','uz']) assert.ok(translations[lang][key]);
assert.ok(!/\b(fetch|XMLHttpRequest|localStorage|sessionStorage)\b/.test(source));
if (process.argv[3]) fs.writeFileSync(process.argv[3], JSON.stringify(cases,null,2));
console.log('PASS: 18 client/terminal/interpreter combinations, 8 invalid inputs, translation completeness, no requests or storage.');
