const fs=await import('node:fs/promises');
const task=await taskSpace(7);
const page=task.page('p1');
await page.goto('http://127.0.0.1:8769/report.html',{waitUntil:'domcontentloaded'});
console.log(await page.snapshot());
console.log(await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-preflight/artifacts/ego-report.png'}));
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-preflight/evidence/browser-report.json',JSON.stringify({url:await page.url(),checked_at:new Date().toISOString(),text:await page.evaluate(()=>document.body.innerText.slice(0,1800))},null,2));
