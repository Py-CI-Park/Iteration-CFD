const task=await taskSpace("A321 layer conditioning continuation 20261107"),p=task.page("p1");
await p.goto("http://127.0.0.1:5185/",{waitUntil:"domcontentloaded"});
console.log({space:task.spaceId,state:(await p.snapshot()).slice(-550)});
