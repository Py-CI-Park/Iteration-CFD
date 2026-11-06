const task=await taskSpace(6);const p=task.page('p1');
await p.waitForFunction(()=>document.body.innerText.includes('research/a321-layers/artifacts/constrained-exact-02/outer.stl'));
await p.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-layers/evidence/studio-outer.png'});
console.log(await p.evaluate(()=>({text:document.body.innerText.slice(-1900),canvas:document.querySelector('canvas')?.width})));
