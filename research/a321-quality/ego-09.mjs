const task=await taskSpace(8);const report=task.page('p2');
await report.reload({waitUntil:'domcontentloaded'});
console.log(await report.evaluate(()=>({title:document.title,hasV5:document.body.innerText.includes('v5'),has66:document.body.innerText.includes('66.203955'),hasPartial:document.body.innerText.includes('PARTIAL'),images:[...document.images].every(n=>n.complete&&n.naturalWidth>0)})));
await report.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/report.png'});
await task.finish({keep:['p1','p2']});
