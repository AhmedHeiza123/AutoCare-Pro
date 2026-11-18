import assert from 'node:assert/strict';
import test from 'node:test';
import configuration from '../vite.config.js';

function withTarget(value,action){
  const previous=process.env.AUTOCARE_API_TARGET;
  if(value===undefined)delete process.env.AUTOCARE_API_TARGET;else process.env.AUTOCARE_API_TARGET=value;
  try{return action();}finally{if(previous===undefined)delete process.env.AUTOCARE_API_TARGET;else process.env.AUTOCARE_API_TARGET=previous;}
}
test('dev/preview refuse to start with an implicit backend target',()=>{
  withTarget(undefined,()=>{
    assert.throws(()=>configuration({command:'serve',isPreview:false}),/AUTOCARE_API_TARGET/);
    assert.throws(()=>configuration({command:'serve',isPreview:true}),/AUTOCARE_API_TARGET/);
  });
});
test('production build does not require or invent a backend target',()=>{
  withTarget(undefined,()=>{
    const config=configuration({command:'build'});
    assert.equal(config.server.proxy,undefined);
    assert.equal(config.preview.proxy,undefined);
  });
});
test('explicit backend origin is used consistently by dev and preview',()=>{
  withTarget('http://127.0.0.1:43681',()=>{
    const config=configuration({command:'serve'});
    for(const mode of ['server','preview']){
      assert.equal(config[mode].host,'127.0.0.1');
      assert.equal(config[mode].proxy['/api'].target,'http://127.0.0.1:43681');
    }
  });
});
test('backend URLs with credentials or ignored paths are rejected',()=>{
  for(const target of ['http://127.0.0.1:43681/ignored','http://user:pass@127.0.0.1:43681','file:///tmp/backend']){
    withTarget(target,()=>assert.throws(()=>configuration({command:'serve'}),/AUTOCARE_API_TARGET/));
  }
});
