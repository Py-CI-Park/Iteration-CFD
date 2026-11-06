const task=await taskSpace(6);const p=task.page('p1');
console.log(await p.evaluate(()=>[...document.querySelectorAll('button')].filter(n=>n.getBoundingClientRect().width>0).map(n=>({text:n.textContent,title:n.title,label:n.getAttribute('aria-label')})).filter(n=>n.title||n.label)));
const report=await task.newPage();console.log({reportLabel:report.label});
await report.goto('http://127.0.0.1:8773/report.html',{waitUntil:'domcontentloaded'});
console.log(await report.evaluate(()=>({title:document.title,heading:document.querySelector('h1')?.textContent,images:[...document.images].map(n=>({src:n.src,ok:n.complete&&n.naturalWidth>0})),hold:document.body.innerText.includes('AIRCRAFT_GPU_HOLD')})));
