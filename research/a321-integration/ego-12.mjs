const task=await taskSpace(4);const page=task.page('p1');
console.log(await page.evaluate(()=>[...document.querySelectorAll('[role=treeitem]')].filter(n=>n.getAttribute('data-path')?.startsWith('research/a321-integration')).map(n=>({text:n.textContent,path:n.getAttribute('data-path')}))));
