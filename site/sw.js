const CACHE='yetkinlik-os-v8';const ASSETS=['./','./index.html','./manifest.json','./icon.svg','./wellness.css','./wellness.js','./software-academy.js','./software-academy.css'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)));self.skipWaiting()});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',event=>{
 if(event.request.method!=='GET'||new URL(event.request.url).origin!==self.location.origin)return;
 // Data and HTML are network-first; never freeze the daily bulletin in the offline cache.
 const u=new URL(event.request.url);
 if(u.pathname.endsWith('/data/news.json')||u.pathname.endsWith('/index.html')||u.pathname.endsWith('/')||u.pathname.endsWith('/software-academy.js')||u.pathname.endsWith('/software-academy.css')){
  event.respondWith(fetch(event.request).catch(()=>caches.match(event.request)));return;
 }
 event.respondWith(caches.match(event.request).then(response=>response||fetch(event.request)));
});