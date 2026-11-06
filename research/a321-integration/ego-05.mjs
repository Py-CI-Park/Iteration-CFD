const task=await taskSpace(4);const page=task.page('p1');
await page.click('loc=role:treeitem[name="a321-shell"]');
console.log((await page.snapshot()).slice(0,10000));
