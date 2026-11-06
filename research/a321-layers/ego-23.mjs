const task=await taskSpace(6);const p=task.page('p1');
await p.click('loc=css:[data-tab-id="geometry:research/a321-layers/artifacts/constrained-exact-02/outer.stl"]');
console.log(await p.evaluate(()=>({outerVisible:document.body.innerText.includes('research/a321-layers/artifacts/constrained-exact-02/outer.stl')})));
const report=task.page('p2');await report.reload({waitUntil:'domcontentloaded'});
console.log(await report.evaluate(()=>({title:document.title,hold:document.body.innerText.includes('AIRCRAFT_GPU_HOLD'),images:[...document.images].every(n=>n.complete&&n.naturalWidth>0)})));
await task.finish({keep:['p1','p2']});
