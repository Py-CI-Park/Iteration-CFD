const task=await taskSpace(10);
const page=task.page('p1');
await page.goto('http://127.0.0.1:8770/report.html',{waitUntil:'domcontentloaded'});
console.log(await page.snapshot());
console.log(await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-shell/artifacts/ego-report.png'}));
