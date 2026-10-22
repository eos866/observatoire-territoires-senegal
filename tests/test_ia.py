import asyncio, json, sys
from playwright.async_api import async_playwright
import os
SP=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
F=sys.argv[1] if len(sys.argv)>1 else SP+'index.html'
MOCK = r"""
window.__calls=[];
const mock=async(input,opts)=>{window.__input=input;const T=opts.tools;const run=async(n,a)=>{const t=T.find(x=>x.name===n);try{const r=await t.execute(a,{signal:new AbortController().signal});window.__calls.push([n,JSON.stringify(r).length]);return r}catch(e){window.__calls.push([n,'ERR '+e.message]);return null}};
  await run('chercher_territoire',{nom:'dakar'});await run('chercher_territoire',{nom:'Tivaoune',niveau:'commune'});
  await run('profil_territoire',{id:'D-mbour'});await run('profil_territoire',{id:'SN',themes:['Habitat']});await run('profil_territoire',{id:'Mbacké'});
  await run('classement',{indicateur:'pop',niveau:'commune',n:60});await run('classement',{indicateur:'gr',niveau:'commune',dans:'SN-TH',ordre:'asc',n:5});
  await run('classement',{indicateur:'pauv',niveau:'departement'});await run('classement',{indicateur:'Densité de population',niveau:'region',min:100});
  await run('comparer',{ids:['SN-DK','D-mbour','C-mbacke-mbacke','SN']});await run('tableau_regional',{tableau:'cuis'});await run('tableau_regional',{tableau:'mig',region:'D-mbour'});
  await run('equipements',{id:'D-mbour'});await run('equipements',{id:'SN-ZG',categorie:'heb'});await run('equipements',{id:'C-mbacke-mbacke',categorie:'Santé'});
  const txt="Voici **la réponse** test.\n\n| Rang | Commune | Valeur |\n|---|---|---|\n| 1 | Touba | 1 000 |\n| 2 | Pikine | 900 |\n\n- point un\n- point *deux*\n\nSources : ANSD, RGPH-5 2023.";
  opts.onText({text:txt.slice(0,20),delta:txt.slice(0,20)});await new Promise(r=>setTimeout(r,50));opts.onText({text:txt,delta:txt.slice(20)});return {text:txt,truncated:false,modelTierApplied:'default'}};
mock.limits=async()=>({maxPromptBytes:262144,tools:{maxCount:20}});
window.claude={use:async n=>n==='sample'?mock:null};
"""
QS=["Quelle est la densité de Kaolack ?","Quelles sont les 10 communes les plus peuplées ?","Classement des régions selon le taux de pauvreté","Compare Thiès et Mbour","Portrait de Ziguinchor",
    "Quelles communes du département de Mbour ont la plus forte croissance ?","Combien d'hôtels à Saint-Louis ?","Où cuisine-t-on le plus au bois ou au charbon ?","Bonjour","Quelle est la population de la commune de Dakar Plateau ?","taux d'électricité ici"]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        errs=[]
        # 1. mode simple
        pg=await b.new_page(viewport={'width':1400,'height':950})
        pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None)
        await pg.route('**/*',lambda r:r.abort() if not r.request.url.startswith('file:') else r.continue_())
        await pg.goto('file://'+F+'#dep-mbour');await pg.wait_for_timeout(800)
        await pg.click('#iaFab');await pg.wait_for_timeout(300)
        print('mode', await pg.inner_text('#iaMode'))
        for q in QS:
            await pg.fill('#iaQ',q);await pg.keyboard.press('Enter');await pg.wait_for_timeout(250)
            t=await pg.evaluate("[...document.querySelectorAll('.ia-msg.assistant')].pop().innerText")
            print('\n### Q:',q,'\n',t[:700])
        await pg.screenshot(path=SP+'tests/shots/ia_local.png')
        await pg.set_viewport_size({'width':390,'height':844});await pg.wait_for_timeout(200)
        print('mobile scrollW',await pg.evaluate('document.documentElement.scrollWidth'))
        await pg.screenshot(path=SP+'tests/shots/ia_local_m.png')
        # 2. mode Claude simulé
        pg2=await b.new_page(viewport={'width':1400,'height':950})
        pg2.on('pageerror',lambda e:errs.append(str(e)))
        await pg2.add_init_script(MOCK)
        await pg2.route('**/*',lambda r:r.abort() if not r.request.url.startswith('file:') else r.continue_())
        await pg2.goto('file://'+F+'#dep-mbour');await pg2.wait_for_timeout(800)
        await pg2.evaluate("setView('ia')");await pg2.wait_for_timeout(300)
        print('\nmode2', await pg2.inner_text('#iaMode'))
        await pg2.click('#iaSugg .chip');await pg2.wait_for_timeout(1500)
        print(json.dumps(await pg2.evaluate('window.__calls')))
        print('rules bytes',await pg2.evaluate('new Blob([window.__input[0].content]).size'),'turns',await pg2.evaluate('window.__input.length'))
        print(await pg2.evaluate("[...document.querySelectorAll('.ia-msg.assistant')].pop().innerText"))
        await pg2.screenshot(path=SP+'tests/shots/ia_claude.png')
        print('errors',errs)
        await b.close()
asyncio.run(main())
