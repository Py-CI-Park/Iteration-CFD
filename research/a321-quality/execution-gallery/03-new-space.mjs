// meteor-cfd - Copyright (c) 2026 Iterations Co., Ltd.
// Source-available; see LICENSE at repository root.
// Teaching and academic research are free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// Provenance: public APIs only; no GPL implementation source consulted.
const task=await taskSpace("A321 roadmap execution 20261108");
const p=task.page("p1");
await p.goto("http://127.0.0.1:5185/",{waitUntil:"domcontentloaded",timeout:30000});
const fs=await import("node:fs/promises");
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/execution-browser-space.json",JSON.stringify({spaceId:task.spaceId,studio:p.label,user_explicit_new_space_permission:true,prior_space10_missing:true},null,2)+"\n");
console.log({space:task.spaceId,studio:p.label});
