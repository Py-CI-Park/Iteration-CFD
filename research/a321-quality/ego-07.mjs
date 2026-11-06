const task=await taskSpace(8);const report=await task.newPage();console.log({reportPage:report.label});
await report.goto('http://127.0.0.1:8774/report.html',{waitUntil:'domcontentloaded'});
console.log(await report.evaluate(()=>({title:document.title,heading:document.querySelector('h1')?.textContent,numeric66:document.body.innerText.includes('66.203955'),hold:document.body.innerText.includes('GPU'),images:[...document.images].map(n=>({src:n.src,ok:n.complete&&n.naturalWidth>0}))})));
await report.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/report.png'});
