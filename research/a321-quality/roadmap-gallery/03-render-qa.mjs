// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10),p=task.page("p1");
const fs=await import("node:fs/promises"),crypto=await import("node:crypto");
const root="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality";
await p.goto("http://127.0.0.1:8776/a321-quality/rebuild-roadmap.html",{waitUntil:"load",timeout:30000});
const state=await p.evaluate(()=>({
 title:document.title,h1:document.querySelectorAll("main h1").length,tables:document.querySelectorAll("main table").length,
 ids:[...document.querySelectorAll("[id]")].map(n=>n.id),
 nav:[...document.querySelectorAll('nav a[href^="#"]')].map(n=>({hash:n.hash,found:!!document.querySelector(n.hash)})),
 diagramChecks:["STATUS DASHBOARD","TEXT TREE","ASCII FLOWCHART","NEXT BATCH","[###-----] 3 / 8"].map(text=>({text,found:document.body.innerText.includes(text)})),
 boundaries:["미리 보장할 수는 없다","R5 생성·새 격자·GPU 계산은 아직 실행하지 않았다","12.6","13.x","ofgpu-lowmach"].map(text=>({text,found:document.body.innerText.includes(text)})),
 links:[...new Set([...document.querySelectorAll("a[href]")].map(n=>n.getAttribute("href")).filter(h=>h&&!/^(https?:|#)/.test(h)))]
}));
if(state.h1!==1||state.tables!==5||new Set(state.ids).size!==state.ids.length||state.nav.some(n=>!n.found)||state.diagramChecks.some(n=>!n.found)||state.boundaries.some(n=>!n.found))throw Error(JSON.stringify(state));
const links=[];
for(const link of state.links){const r=await p.fetch(link,{method:"HEAD"});links.push({link,status:r.status});}
if(links.some(n=>n.status!==200))throw Error(JSON.stringify(links));
const response=await p.fetch("http://127.0.0.1:8776/a321-quality/rebuild-roadmap.html");
const fileSHA=crypto.createHash("sha256").update(await fs.readFile(root+"/rebuild-roadmap.html")).digest("hex");
const servedSHA=crypto.createHash("sha256").update(response.body).digest("hex");
if(fileSHA!==servedSHA)throw Error("SERVED_HTML_CHANGED");
async function capture(name){
 const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
 await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
 await p.cdp("Page.bringToFront");
 await p.screenshot({path:root+"/evidence/"+name+".png"});
}
await capture("rebuild-roadmap-desktop");
await p.click('nav a[href="#flow"]');
await capture("rebuild-roadmap-flow");
await p.cdp("Emulation.setDeviceMetricsOverride",{width:390,height:844,mobile:true,deviceScaleFactor:1});
await p.click('nav a[href="#answer"]');
const mobile=await p.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,preCount:document.querySelectorAll("pre").length}));
if(mobile.scroll>mobile.viewport)throw Error(JSON.stringify(mobile));
await capture("rebuild-roadmap-mobile");
await p.cdp("Emulation.clearDeviceMetricsOverride");
await p.goto("http://127.0.0.1:8776/a321-quality/rebuild-roadmap.html",{waitUntil:"load"});
await fs.writeFile(root+"/evidence/rebuild-roadmap-report-qa.json",JSON.stringify({status:"PASS_PLAN_DOCUMENT_RENDER_AND_LINKS",state,links,linkMethod:"HTTP HEAD",fileSHA,servedSHA,mobile,scope:"planning and read-only inspection; prior143tests not rerun",new_geometry_generated:false,CPU_mesh_run:false,CFD_solver_run:false,GPU_solver_run:false},null,2)+"\n");
console.log({tables:state.tables,links:links.length,mobile,fileSHA});
