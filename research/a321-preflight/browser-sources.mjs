const fs = await import('node:fs/promises');
const root = 'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-preflight';
await fs.mkdir(`${root}/evidence`, {recursive:true});
const task = await taskSpace('A321 CPU preflight research 20261104');
console.log({spaceId:task.spaceId});
const page = task.page('p1');
const sources = [
 ['tutorial','https://www.grc.nasa.gov/www/wind/valid/tutorial/tutorial.html'],
 ['process','https://www.grc.nasa.gov/www/wind/valid/tutorial/analprocess.html'],
 ['verification','https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html'],
 ['validation','https://www.grc.nasa.gov/www/wind/valid/tutorial/valassess.html'],
 ['iterative','https://www.grc.nasa.gov/www/wind/valid/tutorial/iterconv.html'],
 ['grid','https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html'],
];
const ledger=[];
for (const [id,url] of sources) {
 await page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
 const record=await page.evaluate(()=>({title:document.title,url:location.href,text:document.body.innerText,links:[...document.querySelectorAll('a[href]')].map(a=>({label:a.textContent.trim(),url:a.href}))}));
 await fs.writeFile(`${root}/evidence/nasa-${id}.json`,JSON.stringify({...record,accessed_at:new Date().toISOString()},null,2));
 ledger.push({id,url:record.url,title:record.title,chars:record.text.length});
 console.log(ledger.at(-1));
}
await fs.writeFile(`${root}/evidence/nasa-browser-ledger.json`,JSON.stringify(ledger,null,2));
console.log(await page.snapshot());
