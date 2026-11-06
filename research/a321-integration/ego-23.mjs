const task=await taskSpace(4);const page=task.page('p1');
console.log((await page.snapshot()).slice(-5500));
