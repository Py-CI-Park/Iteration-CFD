// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10),p=task.page("p1");
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const overview=await p.evaluate(async()=>{const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");return getViewerApi().getState();});
if(overview.cellCount!==1010837||overview.datasetName!=="snappy-08-owner-diagnostic"||overview.field!=="diagnostic_owner_layer_min")throw Error("WRONG_08_LOADED_STATE");
async function capture(name){
 const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
 await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
 await p.cdp("Page.bringToFront");
 await p.screenshot({path:dir+"/"+name+".png"});
}
await capture("studio-snappy08-layer-map");
const wing=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const r=await api.execute({type:"setCamera",position:[25,13,14],target:[22.8,8,3.9],projection:"perspective"});
 if(!r.ok)throw Error(JSON.stringify(r.error));return api.getState();
});
await capture("studio-snappy08-wing-layers");
const edges=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const r=await api.execute({type:"setRepresentation",mode:"surfaceEdges",patches:["aircraft"],shading:"flat"});
 if(!r.ok)throw Error(JSON.stringify(r.error));return api.getState();
});
await capture("studio-snappy08-wing-grid");
await fs.writeFile(dir+"/studio-snappy08-views.json",JSON.stringify({overview,wing,edges,meaning:"native layer-count diagnostic and aircraft boundary grid, not pressure or full volume mesh",CFD_solver_run:false,earlierLoadWait:"one page.evaluate exceeded wrapper wait; current state was observed ready without repeating load"},null,2)+"\n");
console.log({cells:overview.cellCount,field:overview.field,range:overview.range});
