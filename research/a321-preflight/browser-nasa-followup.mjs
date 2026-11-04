const fs=await import('node:fs/promises');
const root='D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-preflight/evidence';
const task=await taskSpace(7);
const page=task.page('p1');
const index=JSON.parse(await fs.readFile(`${root}/nasa-tutorial.json`,'utf8'));
const links=index.links.filter(l=>/Analysis Process|Consistency|Temporal/.test(l.label));
for(const link of links){
 await page.goto(link.url,{waitUntil:'domcontentloaded'});
 const result=await page.evaluate(()=>({title:document.title,url:location.href,text:document.body.innerText}));
 const id=link.label.includes('Analysis')?'analysis-process':link.label.includes('Consistency')?'consistency':'temporal';
 await fs.writeFile(`${root}/nasa-${id}.json`,JSON.stringify({...result,accessed_at:new Date().toISOString()},null,2));
 console.log({id,...link,chars:result.text.length});
}
console.log(await page.snapshot());
