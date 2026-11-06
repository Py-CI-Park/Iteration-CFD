const task=await taskSpace(8);const p=task.page('p1');
console.log(await p.evaluate(()=>({online:document.body.innerText.slice(-450),geometryTabs:[...document.querySelectorAll('[role=tab]')].map(n=>n.textContent)})));
