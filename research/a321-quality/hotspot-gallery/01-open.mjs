const task=await taskSpace("A321 hotspot and CPU retest");
const p=task.page("p1");
await p.goto("http://127.0.0.1:5185/",{waitUntil:"domcontentloaded"});
console.log({id:task.spaceId,state:(await p.snapshot()).slice(-900)});
