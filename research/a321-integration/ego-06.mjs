const task=await taskSpace(4);const page=task.page('p1');
console.log(await page.evaluate(()=>[...document.querySelectorAll('[role=treeitem]')].filter(n=>/a321-shell|models/.test(n.textContent)).map(n=>({text:n.textContent,expanded:n.getAttribute('aria-expanded'),html:n.outerHTML.slice(0,600)}))));
console.log(await page.snapshot());
