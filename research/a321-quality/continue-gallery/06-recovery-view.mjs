const task=await taskSpace(10),p=task.page("p1");
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
await p.waitForFunction(()=>document.body.innerText.includes("온라인"),undefined,{timeout:30000});
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
const overview=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts"); const api=getViewerApi();
 const commands=[
 {type:"load",path:"research/a321-quality/artifacts/snappy-06-owner-diagnostic",field:"diagnostic_owner_layer_min"},
 {type:"setField",field:"diagnostic_owner_layer_min",range:[0,8],colormap:"turbo"},
 {type:"setRepresentation",mode:"surface",patches:["aircraft"],shading:"flat"},
 {type:"setCamera",position:[49,35,38],target:[22,0,6],projection:"perspective"}
 ];
 for(const cmd of commands){const r=await api.execute(cmd);if(!r.ok)throw Error(JSON.stringify(r.error));}
 return api.getState();
});
if(overview.cellCount!==1011805||overview.field!=="diagnostic_owner_layer_min")throw Error(JSON.stringify(overview));
await p.screenshot({path:dir+"/studio-snappy06-layer-map-20261108.png"});
const wing=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts"); const api=getViewerApi();
 const r=await api.execute({type:"setCamera",position:[25,13,14],target:[22.8,8,3.9],projection:"perspective"});
 if(!r.ok)throw Error(JSON.stringify(r.error));
 return api.getState();
});
await p.screenshot({path:dir+"/studio-snappy06-wing-layers-20261108.png"});
await fs.writeFile(dir+"/studio-recovery-20261108.json",JSON.stringify({overview,wing,meaning:"native mesher layer-count diagnostic, not flow solution",CFDSolverRun:false},null,2)+"\n");
console.log({field:overview.field,cells:overview.cellCount,range:overview.range,patches:overview.patches});
