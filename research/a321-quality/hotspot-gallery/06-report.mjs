const task=await taskSpace(13),p=await task.newPage();
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
await p.goto("http://127.0.0.1:8776/a321-quality/report.html",{waitUntil:"load"});
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label===p.label).targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.evaluate(()=>document.querySelectorAll("details").forEach(n=>n.open=true));
await p.waitForFunction(()=>[...document.images].every(n=>n.complete&&n.naturalWidth>0));
const check=await p.evaluate(()=>({
 title:document.title,images:document.images.length,loaded:[...document.images].every(n=>n.complete&&n.naturalWidth>0),
 ids:[...document.querySelectorAll("[id]")].map(n=>n.id),
 anchors:[...document.querySelectorAll("nav a")].map(n=>({id:n.hash,exists:!!document.querySelector(n.hash)})),
 rows:document.querySelector("main table tbody").rows.length,
 prior:!!document.querySelector("#prior-report"),detail:!!document.querySelector("#detail"),
 texts:[document.querySelector("#prior-report").textContent.includes("33.2675"),document.querySelector("#detail").textContent.includes("66.203955")]
}));
if(!check.loaded||check.rows!==8||new Set(check.ids).size!==check.ids.length||check.anchors.some(n=>!n.exists)||check.texts.some(n=>!n))throw Error(JSON.stringify(check));
await p.evaluate(()=>document.querySelectorAll("details").forEach(n=>n.open=false));
await p.screenshot({path:dir+"/report-hotspots-desktop.png"});
await p.cdp("Emulation.setDeviceMetricsOverride",{width:390,height:844,mobile:true,deviceScaleFactor:1});
const mobile=await p.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
await p.screenshot({path:dir+"/report-hotspots-mobile.png"});
await p.cdp("Emulation.clearDeviceMetricsOverride");
if(mobile.scroll>mobile.width)throw Error(JSON.stringify(mobile));
await fs.writeFile(dir+"/report-hotspots-qa.json",JSON.stringify({check,mobile},null,2)+"\n");
console.log({page:p.label,images:check.images,rows:check.rows,mobile});
