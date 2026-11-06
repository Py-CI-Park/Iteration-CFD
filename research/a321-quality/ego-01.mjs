const task=await taskSpace('R3 coupled mesh quality 20261106');console.log({spaceId:task.spaceId});
const p=task.page('p1');await p.goto('http://127.0.0.1:5183/',{waitUntil:'domcontentloaded'});
console.log((await p.snapshot()).slice(-1300));
