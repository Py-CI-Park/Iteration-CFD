const task=await taskSpace(6);const p=task.page('p1');
console.log(await p.evaluate(()=>[...document.querySelectorAll('button[title="설정"]')].map(n=>({outer:n.outerHTML.slice(0,400),parent:n.parentElement?.className,grandparent:n.parentElement?.parentElement?.className}))));
const report=task.page('p2');await report.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-layers/evidence/report.png'});
