const task=await taskSpace(6);const p=task.page('p1');
await p.click('loc=role:button[name="3D 뷰어로 열기"]');
console.log((await p.snapshot()).slice(-6500));
