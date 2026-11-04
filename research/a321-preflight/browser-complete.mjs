const task=await taskSpace(7);
const page=task.page('p1');
await page.reload({waitUntil:'domcontentloaded'});
console.log(await page.evaluate(()=>({title:document.title,partial:document.body.innerText.includes('PARTIAL'),vertexLimit:document.body.innerText.includes('정점 link')})));
await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-preflight/artifacts/ego-report-final.png'});
await task.finish({keep:['p1']});
