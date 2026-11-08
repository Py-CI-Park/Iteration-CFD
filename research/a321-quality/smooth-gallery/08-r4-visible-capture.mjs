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
await p.waitForFunction(()=>[...document.querySelectorAll(".geometry-info")].some(n=>n.getBoundingClientRect().width>0&&n.innerText.includes("SHELL_R4.stl")));
const info=await p.evaluate(()=>[...document.querySelectorAll(".geometry-info")].find(n=>n.getBoundingClientRect().width>0)?.innerText);
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.screenshot({path:dir+"/studio-smooth-r4-model.png"});
await fs.writeFile(dir+"/studio-smooth-r4-model.json",JSON.stringify({info,display:"Studio flat-shaded geometry preview, auto-fit camera",CFD_solver_run:false,earlierWaitFailure:"first DOM geometry-info was hidden R3 tab; actual visible R4 loaded without reader error"},null,2)+"\n");
console.log(info);
