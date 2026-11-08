// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
// Header comments added after execution; the pre-existing script body is preserved.
// The current file including this header is not a byte-original execution receipt.
const task=await taskSpace(10),p=task.page("p1");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const current=await p.evaluate(()=>[...document.querySelectorAll(".geometry-info")].find(n=>n.getBoundingClientRect().width>0)?.innerText);
if(!current?.includes("SHELL_R4.stl"))throw Error("UNEXPECTED_GEOMETRY_AFTER_CAPTURE_FAILURE");
async function capture(name){
 const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
 await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
 await p.cdp("Page.bringToFront");
 await p.screenshot({path:dir+"/studio-smooth-"+name+"-closeup.png"});
}
await capture("r4");
await p.evaluate(async()=>{const {useUiStore}=await import("/src/state/uiStore.ts");useUiStore.getState().openGeometryTab("research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl");});
await p.waitForFunction(()=>[...document.querySelectorAll(".geometry-info")].some(n=>n.getBoundingClientRect().width>0&&n.innerText.includes("SHELL_R3.stl")));
const rect=await p.evaluate(()=>[...document.querySelectorAll('[data-testid="geometry-tab"] canvas')].find(n=>n.getBoundingClientRect().width>0)?.getBoundingClientRect().toJSON());
await p.mouse.move(rect.x+rect.width/2,rect.y+rect.height/2);
await p.mouse.wheel(0,-700,{label:"inspect reference wing surface"});
await capture("r3");
const fs=await import("node:fs/promises");
await fs.writeFile(dir+"/studio-smooth-model-closeups.json",JSON.stringify({wheelDeltaY:-700,modelPaths:["research/a321-quality/models/A321_AIRFRAME_SHELL_R4.stl","research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"],note:"same auto-fit start and same zoom input; previous R4 capture failed only because window minimized; no second R4 zoom",CFD_solver_run:false},null,2)+"\n");
console.log("MODEL_CLOSEUPS_CAPTURED");
