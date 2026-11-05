const fs=await import('node:fs/promises');
const task=await taskSpace(10);
const page=task.page('p1');
await page.reload({waitUntil:'domcontentloaded'});
const check=await page.evaluate(()=>({title:document.title,heading:document.querySelector('h1')?.textContent,
  hold:document.body.innerText.includes('FIX_FIRST'),modelLinks:[...document.querySelectorAll('a')].filter(a=>a.href.includes('/models/')).map(a=>a.href),
  images:[...document.images].map(i=>({url:i.src,loaded:i.complete&&i.naturalWidth>0}))}));
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-shell/evidence/browser-report-check.json',JSON.stringify({...check,checked_at:new Date().toISOString()},null,2));
console.log(check);
console.log(await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-shell/artifacts/ego-report-final.png'}));
