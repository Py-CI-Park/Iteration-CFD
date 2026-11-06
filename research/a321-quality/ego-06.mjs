const task=await taskSpace(8);const p=task.page('p1');
await p.click('loc=role:button[name="3D 뷰어로 열기"]');
await p.waitForFunction(()=>document.body.innerText.includes('462,113'));
console.log(await p.evaluate(()=>({text:document.body.innerText.slice(-2600),canvas:[...document.querySelectorAll('canvas')].filter(n=>n.width>1).map(n=>({width:n.width,height:n.height}))})));
await p.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/studio-snappy03.png'});
const fs=await import('node:fs/promises');await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/studio-snappy03-dom.json',JSON.stringify(await p.evaluate(()=>({at:new Date().toISOString(),text:document.body.innerText.slice(-2800)})),null,2));
