// meteor-cfd - Copyright (c) 2026 Iterations Co., Ltd.
// Source-available; see LICENSE at repository root.
// Teaching and academic research are free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// Provenance: public APIs only; no GPL implementation source consulted.
const task=await taskSpace("A321 roadmap execution 20261108"),p=task.page("p1");
const fs=await import("node:fs/promises");
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/execution-browser-space.json",JSON.stringify({spaceId:task.spaceId,studio:p.label,user_explicit_new_space_permission:true,prior_space10_missing:true,navigation:"committed interactive, wrapper lifecycle timeout; continued samepage"},null,2)+"\n");
console.log({space:task.spaceId,studio:p.label});
console.log((await p.snapshot()).slice(-1600));
