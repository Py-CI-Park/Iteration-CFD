const task=await taskSpace(4);const page=task.page('p1');
await page.click('loc=css:[data-path="research/a321-integration/artifacts"]');
console.log(await page.evaluate(()=>[...document.querySelectorAll('[role=treeitem]')].filter(n=>n.getAttribute('data-path')?.includes('hybrid')).map(n=>({text:n.textContent,path:n.getAttribute('data-path')}))));
