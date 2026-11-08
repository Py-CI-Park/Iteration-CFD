// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10),p=task.page("p1");
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const loaded=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const r=await api.execute({type:"load",path:"research/a321-quality/artifacts/snappy-10-owner-diagnostic",field:"diagnostic_owner_layer_min"});
 if(!r.ok)throw Error(JSON.stringify(r.error));return api.getState();
});
if(loaded.cellCount!==1011614)throw Error("WRONG_10_MESH");
const overview=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 for(const cmd of [
 {type:"setField",field:"diagnostic_owner_layer_min",range:[0,8],colormap:"turbo"},
 {type:"setRepresentation",mode:"surface",patches:["aircraft"],shading:"flat"},
 {type:"setCamera",position:[49,35,38],target:[22,0,6],projection:"perspective"}]){
 const r=await api.execute(cmd);if(!r.ok)throw Error(JSON.stringify(r.error));}
 return api.getState();
});
async function capture(name){
 const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
 await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
 await p.cdp("Page.bringToFront");await p.screenshot({path:dir+"/"+name+".png"});
}
await capture("studio-snappy10-layer-map");
const edges=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 for(const cmd of [
 {type:"setCamera",position:[25,13,14],target:[22.8,8,3.9],projection:"perspective"},
 {type:"setRepresentation",mode:"surfaceEdges",patches:["aircraft"],shading:"flat"}]){
 const r=await api.execute(cmd);if(!r.ok)throw Error(JSON.stringify(r.error));}
 return api.getState();
});
await capture("studio-snappy10-wing-grid");
await fs.writeFile(dir+"/studio-snappy10-views.json",JSON.stringify({overview,edges,meaning:"sameR4andweightas11, buffer1vs3comparison, native layer diagnostics notCFD",CFD_solver_run:false},null,2)+"\n");
console.log({cells:overview.cellCount,field:overview.field});
