const task=await taskSpace(12), p=task.page("p1");
const base="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const fs=await import("node:fs/promises");
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
const view=cmds=>p.evaluate(async commands=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");
 const api=getViewerApi();
 for(const cmd of commands){const r=await api.execute(cmd);if(!r.ok)throw Error(JSON.stringify(r.error));}
 return api.getState();
},cmds);
const domain=await view([{type:"remove",id:"a321-wing-y10"},{type:"setRepresentation",mode:"wireframe",patches:"all"},{type:"setCamera",preset:"fit",projection:"perspective"}]);
await p.screenshot({path:base+"/studio-20261107-domain.png"});
const aircraft=await view([{type:"setRepresentation",mode:"surfaceEdges",patches:["aircraft"]},{type:"setCamera",position:[49,35,38],target:[22,0,6],projection:"perspective"}]);
await p.screenshot({path:base+"/studio-20261107-airframe-grid.png"});
const wing=await view([{type:"setCamera",position:[25,13,14],target:[22.8,8,3.9],projection:"perspective"}]);
await p.screenshot({path:base+"/studio-20261107-wing.png"});
await fs.writeFile(base+"/studio-20261107-receipt.json",JSON.stringify({domain,aircraft,wing},null,2));
console.log({domain:domain.patches,aircraft:aircraft.patches,wing:wing.camera,cells:wing.cellCount});
