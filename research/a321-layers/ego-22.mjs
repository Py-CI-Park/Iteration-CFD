const task=await taskSpace(6);const p=task.page('p1');
console.log(await p.evaluate(()=>[...document.querySelectorAll('[role="tab"]')].map(n=>({text:n.textContent,outer:n.outerHTML.slice(0,250)}))));
