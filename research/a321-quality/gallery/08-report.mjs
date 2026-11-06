const task=await taskSpace(12);
const p=await task.newPage();
const base="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const fs=await import("node:fs/promises");
await p.goto("http://127.0.0.1:8776/a321-quality/report.html",{waitUntil:"load"});
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label===p.label).targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
const inspect=()=>p.evaluate(()=>({
 title:document.title,
 overviewRows:document.querySelector("#progress+ p+table tbody")?.rows.length??document.querySelector("main table tbody")?.rows.length,
 sections:[...document.querySelectorAll("nav a")].map(n=>({href:n.hash,found:!!document.querySelector(n.hash)})),
 tables:document.querySelectorAll("table").length,
 images:[...document.images].map(n=>({src:n.getAttribute("src"),loaded:n.complete&&n.naturalWidth>0})),
 layoutWidth:document.documentElement.scrollWidth, viewport:innerWidth,
 links:[...document.querySelectorAll('a[href^="../"][href$="report.html"]')].map(n=>n.href)
}));
const desktop=await inspect();
await p.screenshot({path:base+"/report-20261107-desktop.png"});
await p.cdp("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
const mobile=await inspect();
await p.screenshot({path:base+"/report-20261107-mobile.png"});
await p.cdp("Emulation.clearDeviceMetricsOverride");
const links=[];
for(const url of desktop.links){const response=await p.fetch(url);links.push({url,status:response.status});}
const receipt={desktop,mobile,links};
if(desktop.overviewRows!==8||desktop.sections.some(s=>!s.found)||desktop.images.some(i=>!i.loaded)||mobile.layoutWidth>mobile.viewport||links.some(l=>l.status!==200))throw Error(JSON.stringify(receipt));
await fs.writeFile(base+"/report-20261107-qa.json",JSON.stringify(receipt,null,2));
console.log(JSON.stringify({page:p.label,tables:desktop.tables,images:desktop.images.length,links,mobile:[mobile.layoutWidth,mobile.viewport]}));
