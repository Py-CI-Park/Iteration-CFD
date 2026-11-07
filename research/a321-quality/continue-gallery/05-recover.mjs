const task=await taskSpace("A321 recovery 20261108"),p=task.page("p1");
await p.goto("http://127.0.0.1:5185/",{waitUntil:"domcontentloaded"});
console.log({space:task.spaceId,pages:await task.pages()});
console.log((await p.snapshot()).slice(-800));
