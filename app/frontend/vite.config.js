import {defineConfig} from 'vite';

// Only the development server uses this proxy. Production is served by FastAPI
// from the existing app/frontend/dist location, preserving same-origin sessions.
export default defineConfig(({command})=>{
  const target=process.env.AUTOCARE_API_TARGET;
  if(command==='serve'&&!target)throw Error('Set AUTOCARE_API_TARGET explicitly to your isolated backend origin before dev/preview. No installed backend is selected automatically.');
  let proxy;
  if(target){
    let backend;
    try{backend=new URL(target);}catch{throw Error('AUTOCARE_API_TARGET must be an HTTP(S) origin');}
    if(!['http:','https:'].includes(backend.protocol)||backend.username||backend.password||backend.pathname!=='/'||backend.search||backend.hash)throw Error('AUTOCARE_API_TARGET must be a plain HTTP(S) origin without credentials, path, query or fragment');
    proxy={'/api':{target:backend.origin},'/health':{target:backend.origin}};
  }
  return {
  server:{
    host:'127.0.0.1',port:5173,strictPort:true,
    proxy,
    fs:{strict:true},
  },
  preview:{host:'127.0.0.1',port:4173,strictPort:true,proxy},
  // The recovered runtime already contains the original preload polyfill.
  build:{outDir:'dist',emptyOutDir:true,minify:false,sourcemap:false,modulePreload:{polyfill:false}},
  };
});
