const task=await taskSpace(4);const page=task.page('p1');
await page.click('loc=css:[data-path="research/a321-shell/models"]');
console.log((await page.snapshot()).slice(0,12500));
