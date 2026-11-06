const fs=await import('node:fs/promises');const task=await taskSpace(6);const p=task.page('p1');
const result=await p.fetch('/api/datasets/f09bb0ff4261e4ba81ee1bbb091273de8e6b0544');
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-layers/evidence/studio-dataset-status.json',JSON.stringify(result,null,2));console.log(result.body.slice(0,2800));
console.log(await p.evaluate(()=>[...document.querySelectorAll('[role=treeitem]')].filter(n=>n.getAttribute('data-path')?.startsWith('research')).slice(-30).map(n=>({text:n.textContent,path:n.getAttribute('data-path')}))));
