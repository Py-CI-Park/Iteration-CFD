// meteor-cfd - Copyright (c) 2026 Iterations Co., Ltd.
// Source-available; see LICENSE at repository root.
// Teaching and academic research are free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// Provenance: public APIs only; no GPL implementation source consulted.
const task=await taskSpace(10),p=task.page("p1");
await p.evaluate(async()=>{const {useUiStore}=await import("/src/state/uiStore.ts");useUiStore.getState().openGeometryTab("research/a321-quality/rebuild/artifacts/rebuild-r5-a/A321_AIRFRAME_REBUILD_R5_A.stl");});
await p.waitForFunction(()=>[...document.querySelectorAll(".geometry-info")].some(n=>n.getBoundingClientRect().width>0&&n.innerText.includes("REBUILD_R5_A.stl")),undefined,{timeout:60000});
const info=await p.evaluate(()=>[...document.querySelectorAll(".geometry-info")].find(n=>n.getBoundingClientRect().width>0)?.innerText);
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.screenshot({path:"D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/execution-r5-a-studio.png"});
const fs=await import("node:fs/promises");
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/execution-r5-a-studio.json",JSON.stringify({info,meaning:"failed R5-A geometry draft preview; selfintersection4184; not accepted",CFD_solver_run:false,GPU_solver_run:false},null,2)+"\n");
console.log(info);
