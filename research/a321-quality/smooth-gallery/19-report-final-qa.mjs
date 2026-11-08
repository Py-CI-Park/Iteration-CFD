// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10),p=task.page("p2");
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality";
await p.goto("http://127.0.0.1:8776/a321-quality/report.html",{waitUntil:"load",timeout:30000});
await p.evaluate(()=>document.querySelectorAll("details").forEach(n=>n.open=true));
await p.waitForFunction(()=>[...document.images].every(n=>n.complete&&n.naturalWidth>0),undefined,{timeout:30000});
const state=await p.evaluate(()=>({
 title:document.title,h1:document.querySelectorAll("h1").length,
 progressRows:document.querySelector("main table tbody").rows.length,
 archives:document.querySelectorAll("details").length,
 ids:[...document.querySelectorAll("[id]")].map(n=>n.id),
 nav:[...document.querySelectorAll("nav a")].map(n=>({hash:n.hash,found:!!document.querySelector(n.hash)})),
 images:[...document.images].map(n=>({src:n.getAttribute("src"),width:n.naturalWidth,loaded:n.complete&&n.naturalWidth>0})),
 textChecks:["35393","94.07%","1.93","0.250164","09에는 182면","GPU 해석 미실행"].map(text=>({text,found:document.body.innerText.includes(text)})),
 links:[...new Set([...document.querySelectorAll("a[href]")].map(n=>n.getAttribute("href")).filter(s=>s&&!/^(https?:|#)/.test(s)))]
}));
if(state.h1!==1||state.progressRows!==8||state.archives!==4||new Set(state.ids).size!==state.ids.length||state.nav.some(n=>!n.found)||state.images.some(n=>!n.loaded)||state.textChecks.some(n=>!n.found))throw Error(JSON.stringify(state));
const links=[];
for(const link of state.links){const r=await p.fetch(link,{method:"HEAD"});links.push({link,status:r.status});}
if(links.some(n=>n.status!==200))throw Error(JSON.stringify(links.filter(n=>n.status!==200)));
const response=await p.fetch("http://127.0.0.1:8776/a321-quality/report.html");
const fileSHA=crypto.createHash("sha256").update(await fs.readFile(root+"/report.html")).digest("hex");
const servedSHA=crypto.createHash("sha256").update(response.body).digest("hex");
if(fileSHA!==servedSHA)throw Error("SERVED_REPORT_SOURCE_DIFFERS");
await p.evaluate(()=>document.querySelectorAll("details").forEach(n=>n.open=false));
async function capture(name){
 const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p2").targetId});
 await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
 await p.cdp("Page.bringToFront");await p.screenshot({path:root+"/evidence/"+name+".png"});
}
await capture("surface-report-desktop");
await p.click('nav a[href="#studio"]');
await capture("surface-report-gallery-desktop");
await p.cdp("Emulation.setDeviceMetricsOverride",{width:390,height:844,mobile:true,deviceScaleFactor:1});
await p.click('nav a[href="#progress"]');
const mobile=await p.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth}));
if(mobile.scroll>mobile.viewport)throw Error(JSON.stringify(mobile));
await capture("surface-report-mobile");
await p.click('nav a[href="#studio"]');
await capture("surface-report-gallery-mobile");
await p.evaluate(()=>document.querySelectorAll("details").forEach(n=>n.open=true));
const expanded=await p.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,open:document.querySelectorAll("details[open]").length}));
if(expanded.scroll>expanded.viewport||expanded.open!==4)throw Error(JSON.stringify(expanded));
await p.evaluate(()=>document.querySelectorAll("details").forEach(n=>n.open=false));
await p.cdp("Emulation.clearDeviceMetricsOverride");
await p.click('nav a[href="#progress"]');
await fs.writeFile(root+"/evidence/surface-report-qa.json",JSON.stringify({status:"PASS_EGO_REPORT_LAYOUT_AND_ASSET_LINKS",state,links,linkMethod:"HTTP HEAD; images independently decoded in DOM",fileSHA,servedSHA,mobile,expanded,CFD_solver_run:false,GPU_solver_run:false},null,2)+"\n");
console.log({images:state.images.length,links:links.length,mobile,expanded,reportSHA:fileSHA});
