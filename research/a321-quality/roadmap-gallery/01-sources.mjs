// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await claimTaskSpace(10);
const tabs=await task.tabs();
const report=await task.adopt(tabs.find(t=>t.url.includes(":8776/")).page);
const studio=await task.adopt(tabs.find(t=>t.url.includes(":5185/")).page);
console.log({space:task.spaceId,report:report.label,studio:studio.label});
await report.goto("https://www.grc.nasa.gov/www/wind/valid/tutorial/tutorial.html",{waitUntil:"domcontentloaded",timeout:30000});
const nasa=await report.evaluate(()=>({title:document.title,url:location.href,links:[...document.querySelectorAll("a")].map(n=>({text:n.textContent.trim(),url:n.href})).filter(n=>/Overview|Analysis|Verification|Validation|Grid/i.test(n.text))}));
await report.goto("https://docs.blender.org/manual/en/latest/modeling/surfaces/introduction.html",{waitUntil:"domcontentloaded",timeout:30000});
const blender=await report.evaluate(()=>({title:document.title,url:location.href,intro:document.body.innerText.slice(0,1400)}));
const fs=await import("node:fs/promises");
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/rebuild-roadmap-sources.json",JSON.stringify({nasa,blender,scope:"public documentation; no GPL implementation source consulted"},null,2)+"\n");
await report.goto("http://127.0.0.1:8776/a321-quality/report.html",{waitUntil:"domcontentloaded",timeout:30000});
console.log({NASA:nasa.title,Blender:blender.title,NASAlinks:nasa.links});
