const task=await taskSpace(6);const p=task.page('p1');
await p.click('loc=css:[data-path="research/a321-layers"]');
console.log(await p.evaluate(()=>[...document.querySelectorAll('[data-path]')].filter(n=>n.getAttribute('data-path')?.includes('a321-layers')).map(n=>({text:n.textContent,path:n.getAttribute('data-path')}))));
