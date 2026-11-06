const task=await taskSpace(6);const p=task.page('p1');
await p.click('loc=css:[data-testid="viewer-settings-button"]');
await p.click('loc=css:button[title="Section (clip box)"]');
console.log((await p.snapshot()).slice(-8000));
