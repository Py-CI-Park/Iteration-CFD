const task=await taskSpace(13), p=task.page("p3");
const fs=await import("node:fs/promises");
const base="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
await p.cdp("Emulation.clearDeviceMetricsOverride");
await p.reload({waitUntil:"load"});
console.log(await p.evaluate(()=>({title:document.title,has04:document.body.innerText.includes("42.60"),hasHold:document.body.innerText.includes("HOLD"),hasAPI:document.body.innerText.includes("OpenCodex")})));
await p.screenshot({path:base+"/report-hotspots-desktop.png"});
await task.finish({keep:["p1","p3"]});
