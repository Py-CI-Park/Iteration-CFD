const task=await taskSpace(6);const p=task.page('p1');
await p.click('loc=css:[data-path="research/a321-layers/artifacts"]');
await p.waitForSelector('loc=css:[data-path="research/a321-layers/artifacts/constrained-exact-02"]',{state:'visible'});
await p.click('loc=css:[data-path="research/a321-layers/artifacts/constrained-exact-02"]');
await p.waitForSelector('loc=css:[data-path="research/a321-layers/artifacts/constrained-exact-02/outer.stl"]',{state:'visible'});
await p.dblclick('loc=css:[data-path="research/a321-layers/artifacts/constrained-exact-02/outer.stl"]');
console.log(await p.snapshot());
