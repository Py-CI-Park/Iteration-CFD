const fs=await import('node:fs/promises');const task=await taskSpace(4);const page=task.page('p1');
const data=await page.fetch('/api/datasets/c465dea9fc36de1cca243af18efbe29049980e73');
console.log({status:data.status,body:data.body.slice(0,3500)});
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/studio-polyMesh-status.json',JSON.stringify(data,null,2));
