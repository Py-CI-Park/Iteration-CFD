const task=await taskSpace(4);const page=task.page('p1');
await page.click('loc=css:[data-path="research/a321-shell/models/A321_AIRFRAME_SHELL_R2.stl"]');
console.log(await page.snapshot());
