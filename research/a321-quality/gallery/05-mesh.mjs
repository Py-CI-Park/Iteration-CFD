const task=await taskSpace(12),p=task.page("p1");
const base="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const fs=await import("node:fs/promises");
await p.click('loc=role:button[name="3D 뷰어로 열기"]');
await p.waitForFunction(()=>document.body.innerText.includes("462,113"),undefined,{timeout:30000});
await p.selectOption("loc=css:select.v3d-select.rep","surfaceEdges");
await p.screenshot({path:base+"/studio-20261107-domain.png"});
const info=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");
 return getViewerApi().getState();
});
await fs.writeFile(base+"/studio-20261107-domain.json",JSON.stringify(info,null,2));
console.log(info);
