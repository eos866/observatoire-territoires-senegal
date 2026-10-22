import os
import asyncio
from playwright.async_api import async_playwright
SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/'
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)),'shots'),exist_ok=True)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for vw in [(1400,900),(390,844)]:
            ctx=await b.new_context(accept_downloads=True,viewport={'width':vw[0],'height':vw[1]})
            pg=await ctx.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.route('**/*',lambda r:r.abort() if not r.request.url.startswith('file:') else r.continue_())
            await pg.goto('file://'+SP+'index.html');await pg.wait_for_timeout(800)
            await pg.evaluate("S.dataLvl='C';S.dataReg='SN-TH';setView('donnees')");await pg.wait_for_timeout(300)
            await pg.click('#btnDExport');await pg.wait_for_timeout(200)
            await pg.screenshot(path=SP+f'tests/shots/d_{vw[0]}.png')
            async with pg.expect_download() as d: await pg.click('#btnXlsx')
            dl=await d.value;await dl.save_as(SP+'tests/shots/t.xlsx')
            await pg.click('#btnDExport')
            async with pg.expect_download() as d: await pg.click('#btnCsvD')
            dl2=await d.value;await dl2.save_as(SP+'tests/shots/t.csv')
            print(vw,dl.suggested_filename,dl2.suggested_filename,await pg.inner_text('#dataMsg'),errs,await pg.evaluate("document.documentElement.scrollWidth"))
        await b.close()
asyncio.run(main())
