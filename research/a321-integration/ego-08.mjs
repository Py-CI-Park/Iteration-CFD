const task=await taskSpace(4);const page=task.page('p1');
console.log(await page.evaluate(()=>[...document.querySelectorAll('[role=treeitem]')].filter(n=>n.textContent.includes('models')||n.textContent.includes('SHELL')).map(n=>({text:n.textContent,path:n.getAttribute('data-path'),expanded:n.getAttribute('aria-expanded')}))));
console.log(await page.snapshot());
