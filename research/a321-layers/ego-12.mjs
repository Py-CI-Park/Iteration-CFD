const task=await taskSpace(6);const p=task.page('p1');
await p.click('loc=css:[data-path="research/a321-layers/artifacts/constrained-exact-02"]',{button:'right'});
await p.click('loc=role:button[name="새로 고침"]');
await p.click('loc=css:[data-path="research/a321-layers/artifacts/constrained-exact-02/case"]',{button:'right'});
console.log((await p.snapshot()).slice(-5800));
