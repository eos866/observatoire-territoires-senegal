import asyncio, sys, base64, os
from playwright.async_api import async_playwright
SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/'
OUT = SP + 'tests/shots/'; os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)),'shots'),exist_ok=True)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1400, 'height': 1000})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' and 'fonts.googleapis' not in m.text and 'ERR_' not in m.text else None)
        await pg.route('**/*', lambda r: r.abort() if not r.request.url.startswith('file:') else r.continue_())
        await pg.goto('file://' + SP + 'index.html')
        await pg.wait_for_timeout(800)
        await pg.add_style_tag(content='.top{position:static!important}')
        await pg.screenshot(path=OUT + 'explorer.png')
        await pg.evaluate("setLevel('C');select('D-dakar')"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=OUT + 'dakar_C.png')
        await pg.evaluate("zoomBy(1.8)"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=OUT + 'dakar_C_zoom.png')
        await pg.evaluate("select('D-pikine')"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=OUT + 'pikine_C.png')
        await pg.evaluate("setLevel('R');select('SN')")
        # Dakar, échelle communes
        await pg.evaluate("select('D-dakar')"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=OUT + 'dakar_communes.png')
        await pg.evaluate("toggleOsm('sante',true);toggleOsm('educ',true);S.layers.vil=true;drawOsm()"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=OUT + 'dakar_osm.png')
        await pg.evaluate("select('SN-TH')"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=OUT + 'thies_osm.png')
        # rapports
        for tid in sys.argv[1:] or ['SN', 'D-dakar']:
            await pg.evaluate(f"select({tid!r});setView('rapport')"); await pg.wait_for_timeout(400)
            n = await pg.evaluate("document.querySelectorAll('#pages .page').length")
            bad = await pg.evaluate("(document.getElementById('pages').innerText.match(/NaN|undefined|Infinity|null/g)||[]).length")
            # débordements : contenu plus haut que la page en rendu export
            ov = await pg.evaluate("""(()=>{const h=document.createElement('div');h.className='expwrap';h.innerHTML='<div class="pages">'+report(T[S.sel])+'</div>';document.body.appendChild(h);
              const r=[...h.querySelectorAll('.page')].map((p,i)=>{const f=p.querySelector('.pfoot');const last=[...p.children].filter(c=>!c.classList.contains('pfoot')).pop();return [i+1,Math.round(last.getBoundingClientRect().bottom-p.getBoundingClientRect().top),Math.round(f.getBoundingClientRect().top-p.getBoundingClientRect().top)]});h.remove();return r})()""")
            print(tid, 'pages', n, 'mots suspects', bad, 'débordements', [x for x in ov if x[1] > x[2] - 2])
            safe = tid.replace('/', '_')
            pages = await pg.query_selector_all('#pages .page')
            for i, el in enumerate(pages):
                await el.screenshot(path=OUT + f'rep_{safe}_{i+1}.png')
        # docx
        tid = (sys.argv[1:] or ['D-dakar'])[-1]
        await pg.evaluate(f"S.sel={tid!r}")
        b64 = await pg.evaluate("""(async()=>{const blob=await buildDocx(T[S.sel],()=>{});const u=new Uint8Array(await blob.arrayBuffer());let s='';for(let i=0;i<u.length;i+=32768)s+=String.fromCharCode(...u.subarray(i,i+32768));return btoa(s)})()""")
        open(OUT + 'test.docx', 'wb').write(base64.b64decode(b64))
        print('docx', len(b64) * 3 // 4)
        print('ERREURS', errs[:10])
        await b.close()
asyncio.run(main())
