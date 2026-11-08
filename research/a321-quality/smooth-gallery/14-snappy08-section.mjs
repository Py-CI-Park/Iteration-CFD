// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10),p=task.page("p1");
const result=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 for(const cmd of [
 {type:"addSlice",axis:"y",position:10,id:"smooth-08-section-y10"},
 {type:"setRepresentation",mode:"wireframe",patches:[]},
 {type:"setCamera",position:[22.7,20,3.9],target:[22.7,10,3.9],projection:"perspective"}
 ]){const r=await api.execute(cmd);if(!r.ok)throw Error(JSON.stringify(r.error));}
 return api.getState();
});
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.screenshot({path:"D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/studio-snappy08-section-y10.png"});
const fs=await import("node:fs/promises");
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/studio-snappy08-section-y10.json",JSON.stringify({state:result,meaning:"exact geometric cell cut y=10m, native layer diagnostic, not CFD solution",CFD_solver_run:false},null,2)+"\n");
console.log({name:result.datasetName,layers:result.layers,cells:result.cellCount});
