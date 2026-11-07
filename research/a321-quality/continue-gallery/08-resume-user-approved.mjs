const task=await takeOverTaskSpace(10);
console.log({space:task.spaceId,pages:(await task.pages()).map(p=>p.label),tabs:(await task.tabs()).map(t=>({label:t.label,title:t.title,url:t.url,active:t.active}))});
