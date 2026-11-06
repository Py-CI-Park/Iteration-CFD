const task=await taskSpace(6);const p=task.page('p1');
await p.selectOption('loc=css:.v3d select:not([title])','z');
await p.focus('loc=css:input[title="Section position"]');await p.keyboard.press('End');
for(let i=0;i<5;i++)await p.keyboard.press('ArrowLeft');
await p.click('loc=css:[data-testid="viewer-settings-button"]');
await p.click('loc=role:button[name="+z"]');
await p.click('loc=css:[data-testid="viewer-settings-button"]');
console.log(await p.evaluate(()=>({section:document.querySelector('input[title="Section position"]')?.value,text:document.body.innerText.slice(-2100)})));
await p.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-layers/evidence/studio-section-view.png'});
