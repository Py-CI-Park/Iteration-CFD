const task=await taskSpace(4);const studio=task.page('p1');await studio.keyboard.press('Escape');
console.log((await studio.snapshot()).slice(-400));
const page=await task.newPage();console.log({reportLabel:page.label});
await page.goto('http://127.0.0.1:8771/report.html',{waitUntil:'domcontentloaded'});
console.log(await page.evaluate(()=>({title:document.title,heading:document.querySelector('h1')?.textContent,images:[...document.images].map(i=>({url:i.src,loaded:i.complete&&i.naturalWidth>0})),fixFirst:document.body.innerText.includes('FIX_FIRST')})));
await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/report.png'});
