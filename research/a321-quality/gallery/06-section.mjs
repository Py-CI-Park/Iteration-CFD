const task=await taskSpace(12),p=task.page("p1");
const base="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const fs=await import("node:fs/promises");
const tabs=await task.tabs();
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:tabs.find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
const state=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");
 return getViewerApi().getState();
});
if(state.cellCount!==462113)throw Error("wrong mesh");
await p.screenshot({path:base+"/studio-20261107-domain.png"});
const section=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");
 const api=getViewerApi();
 const cut=await api.execute({type:"addSlice",axis:"y",position:10,id:"a321-wing-y10"});
 if(!cut.ok)return {cut};
 const rep=await api.execute({type:"setRepresentation",mode:"wireframe",patches:[]});
 const camera=await api.execute({type:"setCamera",position:[22.7,20,3.9],target:[22.7,10,3.9],projection:"perspective"});
 return {cut,rep,camera};
});
await fs.writeFile(base+"/studio-20261107-receipt.json",JSON.stringify({domain:state,section},null,2));
console.log(JSON.stringify(section).slice(0,2600));
if(section.cut.ok&&section.rep?.ok&&section.camera?.ok) {
 await p.waitForFunction(()=>document.body.innerText.includes("slice y=10"));
 await p.screenshot({path:base+"/studio-20261107-wing.png"});
}
