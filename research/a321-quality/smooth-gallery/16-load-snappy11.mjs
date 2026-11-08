// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10),p=task.page("p1");
const result=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const r=await api.execute({type:"load",path:"research/a321-quality/artifacts/snappy-11-owner-diagnostic",field:"diagnostic_owner_layer_min"});
 if(!r.ok)throw Error(JSON.stringify(r.error));return api.getState();
});
console.log({name:result.datasetName,cells:result.cellCount,field:result.field});
