const task=await taskSpace(6);const p=task.page('p1');
console.log(await p.evaluate(()=>[...document.querySelectorAll('.v3d input,.v3d select')].map(n=>({tag:n.tagName,type:n.type,value:n.value,min:n.min,max:n.max,step:n.step,outer:n.outerHTML.slice(0,280)}))));
