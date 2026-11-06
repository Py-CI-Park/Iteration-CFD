const task = await taskSpace("A321 integrated research report 20261107");
const p = task.page("p1");
await p.goto("http://127.0.0.1:5185/", {waitUntil:"domcontentloaded"});
console.log({id:task.spaceId, state:(await p.snapshot()).slice(-1800)});
