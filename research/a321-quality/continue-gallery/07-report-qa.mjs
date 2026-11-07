const task=await taskSpace(10),p=await task.newPage();
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
await p.goto("http://127.0.0.1:8776/a321-quality/report.html",{waitUntil:"load"});
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label===p.label).targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.evaluate(()=>document.querySelectorAll("details").forEach(n=>n.open=true));
await p.waitForFunction(()=>[...document.images].every(n=>n.complete&&n.naturalWidth>0));
const check=await p.evaluate(()=>({
 title:document.title,rows:document.querySelector("main table tbody")?.rows.length,
 latest:document.querySelector("main h1")?.textContent,
 includes30:document.body.innerText.includes("30 m/s"),includes92:document.body.innerText.includes("92.76%"),
 mean3:document.body.innerText.includes("3.14"),
 anchors:[...document.querySelectorAll("nav a")].map(n=>({hash:n.hash,found:!!document.querySelector(n.hash)})),
 ids:[...document.querySelectorAll("[id]")].map(n=>n.id),
 allImages:[...document.images].map(n=>({src:n.getAttribute("src"),loaded:n.complete&&n.naturalWidth>0})),
 previous:document.querySelectorAll("details").length,
 localLinks:[...new Set([...document.querySelectorAll('a[href]')].map(n=>n.getAttribute("href")).filter(h=>h&&!/^(?:https?:|#)/.test(h)))],
}));
if(check.rows!==8||!check.includes30||!check.includes92||!check.mean3||check.previous!==3||check.anchors.some(n=>!n.found)||new Set(check.ids).size!==check.ids.length||check.allImages.some(n=>!n.loaded))throw Error(JSON.stringify(check));
const linkStatus=[];
for(const link of check.localLinks){const r=await p.fetch(link);linkStatus.push({link,status:r.status});}
if(linkStatus.some(n=>n.status!==200))throw Error(JSON.stringify(linkStatus.filter(n=>n.status!==200)));
await p.evaluate(()=>document.querySelectorAll("details").forEach(n=>n.open=false));
await p.screenshot({path:dir+"/report-conditioning-desktop-20261108.png"});
await p.cdp("Emulation.setDeviceMetricsOverride",{width:390,height:844,mobile:true,deviceScaleFactor:1});
const mobile=await p.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
await p.screenshot({path:dir+"/report-conditioning-mobile-20261108.png"});
await p.cdp("Emulation.clearDeviceMetricsOverride");
if(mobile.width<mobile.scroll)throw Error(JSON.stringify(mobile));
await fs.writeFile(dir+"/report-conditioning-qa-20261108.json",JSON.stringify({check,linkStatus,mobile},null,2)+"\n");
console.log({page:p.label,images:check.allImages.length,links:linkStatus.length,mobile});
