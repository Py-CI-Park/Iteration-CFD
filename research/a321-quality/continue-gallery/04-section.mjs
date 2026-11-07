const task=await taskSpace(15),p=task.page("p1");
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const result=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const cut=await api.execute({type:"addSlice",axis:"y",position:10,id:"layer-diagnostic-cut-y10"});
 if(!cut.ok)return {cut};
 const rep=await api.execute({type:"setRepresentation",mode:"wireframe",patches:[]});
 const camera=await api.execute({type:"setCamera",position:[22.7,20,3.9],target:[22.7,10,3.9],projection:"perspective"});
 return {cut,rep,camera,state:api.getState()};
});
await fs.writeFile(dir+"/owner-diagnostic-slice-attempt.json",JSON.stringify(result,null,2)+"\n");
if(!result.cut.ok)throw Error(JSON.stringify(result.cut.error));
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.screenshot({path:dir+"/studio-owner-diagnostic-slice.png"});
console.log({layers:result.state.layers,message:result.state.message});
