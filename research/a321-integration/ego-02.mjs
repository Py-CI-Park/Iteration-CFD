const task=await taskSpace(4);
const page=task.page('p1');
await page.goto('http://127.0.0.1:5183/',{waitUntil:'domcontentloaded',timeout:30000});
const tabs=await task.tabs();
const w=await task.cdp('Browser.getWindowForTarget',{targetId:tabs.find(t=>t.label==='p1').targetId});
await task.cdp('Browser.setWindowBounds',{windowId:w.windowId,bounds:{windowState:'normal'}});
await page.cdp('Page.bringToFront');
console.log(await page.snapshot());
