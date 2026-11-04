const fs=await import('node:fs/promises');
const task=await taskSpace(7);
const page=task.page('p1');
const check=await page.evaluate(()=>({
 title:document.title,
 sections:[...document.querySelectorAll('h2')].map(n=>n.textContent),
 nasaLinks:[...document.querySelectorAll('a')].filter(a=>a.href.includes('grc.nasa.gov')).map(a=>({label:a.textContent,url:a.href})),
 hasFixFirst:document.body.innerText.includes('FIX_FIRST'),
 sectionsImage:[...document.images].map(i=>({src:i.src,loaded:i.complete&&i.naturalWidth>0}))
}));
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-preflight/evidence/browser-report-check.json',JSON.stringify(check,null,2));
console.log(check);
