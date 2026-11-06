const fs=await import('node:fs/promises');const task=await taskSpace(6);const p=task.page('p1');
console.log(await p.evaluate(()=>({text:document.body.innerText.slice(-2400),canvas:[...document.querySelectorAll('canvas')].filter(n=>n.width>1).map(n=>({width:n.width,height:n.height}))})));
await p.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-layers/evidence/studio-polyMesh.png'});
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-layers/evidence/studio-polyMesh-dom.json',JSON.stringify(await p.evaluate(()=>({text:document.body.innerText.slice(-3000),at:new Date().toISOString()})),null,2));
