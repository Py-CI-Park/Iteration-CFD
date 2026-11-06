const task=await taskSpace(4);const page=task.page('p1');
await page.click('loc=role:treeitem[name="research"]');
console.log(await page.snapshot());
