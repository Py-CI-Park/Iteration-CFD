const task=await taskSpace(4);const page=task.page('p1');
await page.click('loc=css:[data-path="research/a321-integration/artifacts/hybrid-r5/case"]',{button:'right'});
console.log(await page.snapshot());
