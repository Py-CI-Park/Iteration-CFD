// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
// Header comments added after execution; the pre-existing script body is preserved.
// The current file including this header is not a byte-original execution receipt.
const task=await taskSpace(10),p=task.page("p1");
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const captures=[];
for(const [name,path] of [
 ["r4","research/a321-quality/models/A321_AIRFRAME_SHELL_R4.stl"],
 ["r3","research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"]]){
 await p.evaluate(async path=>{const {useUiStore}=await import("/src/state/uiStore.ts");useUiStore.getState().openGeometryTab(path);},path);
 await p.waitForFunction(path=>[...document.querySelectorAll(".geometry-info")].some(n=>n.getBoundingClientRect().width>0&&n.innerText.includes(path)),path);
 const rect=await p.evaluate(()=>[...document.querySelectorAll('[data-testid="geometry-tab"] canvas')].find(n=>n.getBoundingClientRect().width>0)?.getBoundingClientRect().toJSON());
 if(!rect)throw Error("NO_VISIBLE_GEOMETRY_CANVAS");
 await p.mouse.move(rect.x+rect.width/2,rect.y+rect.height/2);
 await p.mouse.wheel(0,-700,{label:"inspect wing surface closer"});
 await p.screenshot({path:dir+"/studio-smooth-"+name+"-closeup.png"});
 captures.push({name,path,rect,wheelDeltaY:-700,note:"same auto-fit starting view and wheel input; geometry preview uses flat shading"});
}
await fs.writeFile(dir+"/studio-smooth-model-closeups.json",JSON.stringify({captures,CFD_solver_run:false},null,2)+"\n");
console.log(captures.map(c=>({name:c.name,path:c.path})));
