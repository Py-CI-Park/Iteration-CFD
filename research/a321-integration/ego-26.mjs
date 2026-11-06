const fs=await import('node:fs/promises');const task=await taskSpace(4);const page=task.page('p2');
const tabs=await task.tabs();const w=await task.cdp('Browser.getWindowForTarget',{targetId:tabs.find(t=>t.label==='p2').targetId});
await task.cdp('Browser.setWindowBounds',{windowId:w.windowId,bounds:{windowState:'normal'}});await page.cdp('Page.bringToFront');
await page.screenshot({path:'D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/report.png'});
const check=await page.evaluate(()=>({title:document.title,fixFirst:document.body.innerText.includes('FIX_FIRST'),images:[...document.images].map(i=>({url:i.src,loaded:i.complete&&i.naturalWidth>0}))}));
await fs.writeFile('D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-integration/evidence/report-browser-check.json',JSON.stringify({...check,at:new Date().toISOString()},null,2));console.log(check);
