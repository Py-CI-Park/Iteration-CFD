// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
// Header comments added after execution; the pre-existing script body is preserved.
// The current file including this header is not a byte-original execution receipt.
const task=await claimTaskSpace(10);
console.log({space:task.spaceId,tabs:(await task.tabs()).map(t=>({label:t.label,title:t.title,url:t.url}))});
