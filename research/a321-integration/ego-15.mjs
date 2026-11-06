const fs=await import('node:fs/promises');const task=await taskSpace(4);const page=task.page('p1');
console.log(await page.evaluate(()=>({text:document.body.innerText.slice(-2400),canvas:document.querySelector('canvas')?.width})));
await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/studio-r3.png'});
const r=await page.fetch('/api/geometry/open',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({path:'research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl'})});
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/studio-r3.json',JSON.stringify({at:new Date().toISOString(),response:r},null,2));
