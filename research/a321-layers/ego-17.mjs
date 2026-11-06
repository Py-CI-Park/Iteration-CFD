const task=await taskSpace(6);const p=task.page('p1');
await p.click('loc=css:[data-testid="viewer-settings-button"]');
console.log((await p.snapshot()).slice(-11000));
