const task=await taskSpace(8);const p=task.page('p1');
console.log(await p.evaluate(()=>[...document.querySelectorAll('[data-path]')].filter(n=>n.getAttribute('data-path')?.includes('a321-quality')).map(n=>({text:n.textContent,path:n.getAttribute('data-path')}))));
const r=await p.fetch('/api/datasets/open',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({path:'research/a321-quality/artifacts/snappy-01'})});
console.log(r.body);const fs=await import('node:fs/promises');await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/studio-snappy01-open.json',JSON.stringify(r,null,2));
