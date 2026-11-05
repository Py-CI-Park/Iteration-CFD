const task=await taskSpace('A321 aerodynamic shell 20261105');
console.log({spaceId:task.spaceId});
const page=task.page('p1');
await page.goto('https://www.grc.nasa.gov/www/wind/valid/tutorial/process.html',{waitUntil:'domcontentloaded'});
console.log(await page.snapshot());
