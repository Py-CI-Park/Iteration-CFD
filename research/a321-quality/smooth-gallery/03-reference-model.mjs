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
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.dblclick('[data-path="research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"]');
await p.waitForSelector('[data-testid="geometry-tab"] .geometry-info',{state:"visible"});
console.log((await p.snapshot()).slice(-4200));
await p.screenshot({path:dir+"/studio-smooth-reference-r3.png"});
await fs.writeFile(dir+"/studio-smooth-reference-r3.json",JSON.stringify(await p.evaluate(()=>({geometry:document.querySelector(".geometry-info")?.innerText,canvas:!!document.querySelector('[data-testid="geometry-tab"] canvas')})),null,2)+"\n");
