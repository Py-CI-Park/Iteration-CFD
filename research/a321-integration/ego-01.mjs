const task=await taskSpace('A321 Studio surface and mesh 20261106');
console.log({spaceId:task.spaceId});
const page=task.page('p1');
await page.goto('http://127.0.0.1:5183/',{waitUntil:'domcontentloaded',timeout:30000});
console.log(await page.snapshot());
