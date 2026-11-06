const task=await taskSpace(4);const page=task.page('p1');
console.log(await page.evaluate(()=>[...document.querySelectorAll('[role=treeitem]')].filter(n=>n.textContent.includes('R3')).map(n=>({text:n.textContent,path:n.getAttribute('data-path')}))));
await page.click('loc=css:[data-path="research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"]');
console.log(await page.snapshot());
