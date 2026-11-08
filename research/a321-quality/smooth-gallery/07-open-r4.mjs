// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
// Header comments added after execution; the pre-existing script body is preserved.
// The current file including this header is not a byte-original execution receipt.
const task=await taskSpace(10),p=task.page("p1");
await p.evaluate(async()=>{
 const {useUiStore}=await import("/src/state/uiStore.ts");
 useUiStore.getState().openGeometryTab("research/a321-quality/models/A321_AIRFRAME_SHELL_R4.stl");
});
await p.waitForFunction(()=>document.querySelector(".geometry-info")?.innerText.includes("SHELL_R4.stl"),undefined,{timeout:30000});
const info=await p.evaluate(()=>document.querySelector(".geometry-info")?.innerText);
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.screenshot({path:"D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/studio-smooth-r4-model.png"});
const fs=await import("node:fs/promises");
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/studio-smooth-r4-model.json",JSON.stringify({info,display:"Studio flat-shaded geometry preview, auto-fit camera",CFD_solver_run:false},null,2)+"\n");
console.log(info);
