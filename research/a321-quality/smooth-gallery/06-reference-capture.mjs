// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
// Header comments added after execution; the pre-existing script body is preserved.
// The current file including this header is not a byte-original execution receipt.
const task=await taskSpace(10),p=task.page("p1");
await p.waitForFunction(()=>document.body.innerText.includes("온라인"),undefined,{timeout:30000});
await p.dblclick('[data-path="research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"]');
await p.waitForSelector('[data-testid="geometry-tab"] .geometry-info',{state:"visible",timeout:30000});
console.log(await p.evaluate(()=>({info:document.querySelector(".geometry-info")?.innerText,rect:document.querySelector('[data-testid="geometry-tab"] canvas')?.getBoundingClientRect().toJSON()})));
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.screenshot({path:"D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/studio-smooth-reference-r3.png"});
