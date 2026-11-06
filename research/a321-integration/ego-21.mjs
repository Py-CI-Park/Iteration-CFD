const task=await taskSpace(4);const page=task.page('p1');
console.log(await page.evaluate(()=>[...document.querySelectorAll('[role=treeitem]')].filter(n=>n.getAttribute('data-path')?.includes('hybrid-r5')).map(n=>({text:n.textContent,path:n.getAttribute('data-path')}))));
