const task=await taskSpace('R3 boundary layer quality 20261106');console.log({spaceId:task.spaceId});
const page=task.page('p1');await page.goto('http://127.0.0.1:5183/',{waitUntil:'domcontentloaded'});
const tabs=await task.tabs();const w=await task.cdp('Browser.getWindowForTarget',{targetId:tabs.find(t=>t.label==='p1').targetId});
await task.cdp('Browser.setWindowBounds',{windowId:w.windowId,bounds:{windowState:'normal'}});await page.cdp('Page.bringToFront');
console.log((await page.snapshot()).slice(-1800));
