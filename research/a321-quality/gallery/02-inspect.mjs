const task = await taskSpace(12);
const p = task.page("p1");
console.log((await p.snapshot()).slice(0,5400));
console.log(await p.evaluate(()=>[...document.querySelectorAll("[data-path]")].slice(-15).map(n=>n.getAttribute("data-path"))));
