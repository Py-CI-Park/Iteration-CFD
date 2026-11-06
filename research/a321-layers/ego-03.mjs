const fs=await import('node:fs/promises');const task=await taskSpace(6);const p=task.page('p1');
await p.reload({waitUntil:'domcontentloaded'});
console.log(await p.evaluate(()=>[...document.querySelectorAll('[role=treeitem]')].filter(n=>n.getAttribute('data-path')?.startsWith('research')).slice(0,15).map(n=>({text:n.textContent,path:n.getAttribute('data-path')}))));
const r=await p.fetch('/api/datasets/open',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({path:'research/a321-layers/artifacts/constrained-exact-02/case'})});
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-layers/evidence/studio-dataset-open.json',JSON.stringify(r,null,2));console.log(r);
