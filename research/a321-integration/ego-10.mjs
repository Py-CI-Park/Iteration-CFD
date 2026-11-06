const fs=await import('node:fs/promises');const task=await taskSpace(4);const page=task.page('p1');
console.log(await page.evaluate(()=>({text:document.body.innerText.slice(-4000),canvas:[...document.querySelectorAll('canvas')].map(c=>({w:c.width,h:c.height}))})));
console.log(await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/studio-r2.png'}));
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/studio-r2.json',JSON.stringify({url:await page.url(),at:new Date().toISOString(),text:await page.evaluate(()=>document.body.innerText.slice(-5000))},null,2));
