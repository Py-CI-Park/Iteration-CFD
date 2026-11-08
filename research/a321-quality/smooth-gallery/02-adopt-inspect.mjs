// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
// Header comments added after execution; the pre-existing script body is preserved.
// The current file including this header is not a byte-original execution receipt.
const task=await taskSpace(10);
const tabs=await task.tabs();
const studio=await task.adopt(tabs.find(t=>t.url==="http://127.0.0.1:5185/").page);
const report=await task.adopt(tabs.find(t=>t.url.includes(":8776/")).page);
console.log({studio:studio.label,report:report.label});
console.log((await studio.snapshot()).slice(0,13000));
