const task=await taskSpace(15),p=task.page("p1");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const fs=await import("node:fs/promises");
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
const result=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts"); const api=getViewerApi();
 const r=await api.execute({type:"setRepresentation",mode:"surface",patches:["aircraft"],shading:"flat"});
 if(!r.ok)throw Error(JSON.stringify(r.error));
 return api.getState();
});
if(result.field!=="diagnostic_owner_layer_min")throw Error("wrong field");
await p.screenshot({path:dir+"/studio-owner-layer-count-flat.png"});
const wing=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const r=await api.execute({type:"setCamera",position:[25,13,14],target:[22.8,8,3.9],projection:"perspective"});
 if(!r.ok)throw Error(JSON.stringify(r.error));
 return api.getState();
});
await p.screenshot({path:dir+"/studio-owner-wing-layers.png"});
await fs.writeFile(dir+"/owner-diagnostic-studio-views.json",JSON.stringify({overview:result,wing,meaning:"layer count diagnostic only, not pressure",solverRun:false},null,2)+"\n");
console.log({field:wing.field,range:wing.range,source:wing.source,cells:wing.cellCount});
