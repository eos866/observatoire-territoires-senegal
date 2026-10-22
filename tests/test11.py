import os
import asyncio
from playwright.async_api import async_playwright
SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/'
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)),'shots'),exist_ok=True)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for vw in [(1400,1000),(390,844)]:
            ctx=await b.new_context(accept_downloads=True,viewport={'width':vw[0],'height':vw[1]})
            pg=await ctx.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
            pg.on('console',lambda m: errs.append(m.text) if m.type=='error' and 'ERR_' not in m.text else None)
            await pg.route('**/*',lambda r:r.abort() if not r.request.url.startswith('file:') else r.continue_())
            await pg.goto('file://'+SP+'index.html#dep-mbour');await pg.wait_for_timeout(800)
            await pg.add_style_tag(content='.top{position:static!important}')
            W=vw[0]
            # carte
            await pg.evaluate("S.rep='circ';S.ind='pop';renderMapCtl();colorMap()");await pg.wait_for_timeout(200)
            await pg.screenshot(path=SP+f'tests/shots/m11_circ_{W}.png')
            await pg.evaluate("S.rep='choro';S.ind='dens';S.ind2='heb';renderMapCtl();colorMap()");await pg.wait_for_timeout(200)
            await pg.screenshot(path=SP+f'tests/shots/m11_bi_{W}.png')
            if W>1000:
                async with pg.expect_download() as d: await pg.click('#btnMapPng')
                dl=await d.value;await dl.save_as(SP+'tests/shots/map.png');print('png',dl.suggested_filename)
                await pg.click('#zfs');await pg.wait_for_timeout(300);await pg.screenshot(path=SP+'tests/shots/m11_fs.png');await pg.keyboard.press('Escape')
            # analyse
            await pg.evaluate("setView('analyse')");await pg.wait_for_timeout(400)
            await pg.screenshot(path=SP+f'tests/shots/an_{W}.png',full_page=True)
            await pg.click('#anScope button[data-s="reg"]');await pg.wait_for_timeout(200)
            # tdb
            await pg.evaluate("setView('tdb')");await pg.wait_for_timeout(400)
            await pg.screenshot(path=SP+f'tests/shots/tdb_{W}.png',full_page=True)
            await pg.select_option('#tdbInd','r_cuis');await pg.select_option('#tdbTy','donut');await pg.click('#tdbAdd');await pg.wait_for_timeout(200)
            n=await pg.evaluate("curTdb().w.length")
            await pg.click('#tdbNew');await pg.fill('#renIn','Mon TDB test');await pg.click('#renOk');await pg.wait_for_timeout(100)
            await pg.select_option('#tdbInd','educ');await pg.select_option('#tdbTy','gauge');await pg.click('#tdbAdd')
            print('tdb',n,await pg.evaluate("TDB.map(d=>d.name+':'+d.w.length).join(' | ')"),await pg.evaluate("localStorage.getItem('obs-tdb-v1')!=null"))
            if W>1000:
                async with pg.expect_download() as d: await pg.click('#tdbXls')
                dl=await d.value;await dl.save_as(SP+'tests/shots/tdb.xlsx')
            # stratégie
            await pg.evaluate("setView('strat')");await pg.wait_for_timeout(300)
            await pg.click('#stNew');await pg.click('#stRenOk');await pg.wait_for_timeout(200)
            await pg.fill('[data-l="ecoles"]','20');await pg.press('[data-l="ecoles"]','Tab');await pg.wait_for_timeout(200)
            await pg.fill('[data-l="raccord"]','5000');await pg.press('[data-l="raccord"]','Tab');await pg.wait_for_timeout(200)
            await pg.fill('[data-l="logts"]','4000');await pg.press('[data-l="logts"]','Tab');await pg.wait_for_timeout(200)
            await pg.click('#stGd');await pg.wait_for_timeout(200)
            # glisser le point 2050
            h=await pg.query_selector('#stSvg .hdl[data-i="4"]');bb=await h.bounding_box()
            await pg.mouse.move(bb['x']+bb['width']/2,bb['y']+bb['height']/2);await pg.mouse.down();await pg.mouse.move(bb['x']+bb['width']/2,bb['y']-40,steps=5);await pg.mouse.up();await pg.wait_for_timeout(300)
            print('g',await pg.evaluate("STR[0].g"))
            await pg.screenshot(path=SP+f'tests/shots/st_{W}.png',full_page=True)
            await pg.click('#stV button[data-v="el"]');await pg.wait_for_timeout(200)
            await pg.screenshot(path=SP+f'tests/shots/st_el_{W}.png',full_page=False)
            if W>1000:
                async with pg.expect_download() as d: await pg.click('#stXls')
                dl=await d.value;await dl.save_as(SP+'tests/shots/st.xlsx')
            for v in ['explorer','rapport','comparer','donnees','sources']: await pg.evaluate(f"setView('{v}')")
            await pg.evaluate("select('SN');setView('analyse')");await pg.evaluate("setView('tdb')");await pg.evaluate("setView('strat')")
            await pg.evaluate("select(communes.find(c=>c.name==='Saly Portudal').id);setView('analyse')");await pg.evaluate("setView('tdb')");await pg.evaluate("setView('strat')")
            print(vw,'scrollW',await pg.evaluate("document.documentElement.scrollWidth"),'err',errs)
        await b.close()
asyncio.run(main())
