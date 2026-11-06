const task=await taskSpace(4);const page=task.page('p1');
const resp=await page.fetch('/api/datasets/open',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({path:'research/a321-integration/artifacts/hybrid-r5/case'})});
console.log({status:resp.status,body:resp.body});
const fs=await import('node:fs/promises');
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/studio-polyMesh-open.json',JSON.stringify({at:new Date().toISOString(),response:resp},null,2));
console.log(await page.snapshot());
