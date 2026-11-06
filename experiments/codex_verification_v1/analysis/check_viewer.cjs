const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { pathToFileURL } = require('url');
const { chromium } = require('/home/grf/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = path.resolve(__dirname, '..');

(async () => {
  const browser = await chromium.launch({headless:true, executablePath:'/usr/bin/google-chrome', args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors = [], external = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if(m.type()==='error') errors.push(m.text()); });
    page.on('request', r => { if(/^https?:/.test(r.url())) external.push(r.url()); });
    const target = pathToFileURL(path.join(root, 'viewer.html')).href;
    await page.goto(target);
    assert.strictEqual(page.url(), target);
    const items = JSON.parse(fs.readFileSync(path.join(root,'prompts/dev_items.json'),'utf8'));
    const keys = new Map(JSON.parse(fs.readFileSync(path.join(root,'keys/dev_keys.json'),'utf8')).map(k=>[k.item_id,k.correct_action]));
    assert.strictEqual(await page.locator('#case option').count(),40);
    let checked = 0;
    for(const [i,item] of items.entries()) {
      await page.selectOption('#case',String(i));
      assert.strictEqual(await page.locator('#dossier').textContent(),item.public_text);
      assert.strictEqual(await page.locator('#key').textContent(),'规则答案：'+keys.get(item.item_id));
      assert.strictEqual(await page.locator('.response').count(),5);
      for(const [j,proc] of ['P0','P1','P3','P7','P8'].entries()) {
        const raw = JSON.parse(fs.readFileSync(path.join(root,'runs/dev',item.item_id+'_r1',proc,'record.json'),'utf8'));
        const card = page.locator('.response').nth(j);
        assert((await card.locator('h2').textContent()).startsWith(proc+' · '));
        assert((await card.locator('.result').textContent()).startsWith('选择 '+raw.parsed.action+' · '));
        assert.strictEqual(await card.locator('p').nth(1).textContent(),raw.parsed.brief_justification);
        assert.strictEqual(await card.locator('p').nth(2).textContent(),'引用：'+raw.parsed.cited_sources.join('、'));
        assert((await card.locator('.meta').textContent()).includes(raw.attempts.at(-1).thread_ids[0]));
        if(proc!=='P0') assert((await card.locator('.meta').textContent()).includes(raw.first_sha256));
        checked++;
      }
    }
    await page.selectOption('#case','0');
    await page.screenshot({path:path.join(root,'audits/viewer_desktop.png'),fullPage:false});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(root,'audits/viewer_mobile.png'),fullPage:false});
    const overflow = await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
    assert(!overflow,'Mobile layout overflows horizontally');
    assert.strictEqual(errors.length,0,errors.join('\n'));
    assert.strictEqual(external.length,0,'Offline viewer requested network resources');
    const result = {passed:true,target,title:await page.title(),items:items.length,checked_responses:checked,console_errors:errors,external_requests:external,mobile_overflow:overflow,browser:'Existing Chrome binary, new isolated headless profile for this new local artifact; no user tab/profile modified',created_utc:new Date().toISOString()};
    fs.writeFileSync(path.join(root,'audits/viewer_check.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1);});
