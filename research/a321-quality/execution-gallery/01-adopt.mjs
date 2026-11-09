// meteor-cfd - Copyright (c) 2026 Iterations Co., Ltd.
// Source-available; see LICENSE at repository root.
// Teaching and academic research are free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// Provenance: public APIs only; no GPL implementation source consulted.
const task=await taskSpace(10);
const tabs=await task.tabs();
const studio=await task.adopt(tabs.find(t=>t.url.includes(":5185/")).page);
const report=await task.adopt(tabs.find(t=>t.url.includes(":8776/")).page);
console.log({space:task.spaceId,studio:studio.label,report:report.label});
