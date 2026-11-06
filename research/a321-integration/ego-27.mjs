const task=await taskSpace(4);const page=task.page('p2');
await page.reload({waitUntil:'domcontentloaded'});
console.log(await page.evaluate(()=>({title:document.title,fixFirst:document.body.innerText.includes('FIX_FIRST'),wallContract:document.body.innerText.includes('aircraft wall')})));
await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/report-final.png'});
