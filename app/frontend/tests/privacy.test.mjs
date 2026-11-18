import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import path from 'node:path';

test('account-bound cleanup removes private draft and cached records but preserves language',async()=>{
  const file=path.resolve('src/security/session-privacy.js');
  assert.ok(fs.existsSync(file),'Session privacy cleanup is missing');
  const {clearPrivateClientState}=await import(pathToFileURL(file));
  const saved=new Map([['autocare.reception.draft','PRIVATE CUSTOMER'],['autocare.lang','ar']]);
  const cached=new Map([['customers','PRIVATE RECORDS']]);
  clearPrivateClientState({clear(){cached.clear();}},{removeItem:key=>saved.delete(key)});
  assert.equal(saved.has('autocare.reception.draft'),false);
  assert.equal(cached.size,0);
  assert.equal(saved.get('autocare.lang'),'ar');
});
test('blocked browser storage does not prevent cache cleanup',async()=>{
  const file=path.resolve('src/security/session-privacy.js');
  assert.ok(fs.existsSync(file),'Session privacy cleanup is missing');
  const {clearPrivateClientState}=await import(pathToFileURL(file));
  const cached=new Map([['settings','PRIVATE SETTINGS']]);
  assert.doesNotThrow(()=>clearPrivateClientState({clear(){cached.clear();}},{removeItem(){throw Error('Storage blocked');}}));
  assert.equal(cached.size,0);
});
test('account reset emits a fresh non-secret signal for other tabs',async()=>{
  const {clearPrivateClientState}=await import(pathToFileURL(path.resolve('src/security/session-privacy.js')));
  const saved=new Map();
  const storage={removeItem:key=>saved.delete(key),setItem:(key,value)=>saved.set(key,value)};
  clearPrivateClientState({clear(){}},storage);
  const first=saved.get('autocare.session.reset');
  assert.equal(typeof first,'string');
  clearPrivateClientState({clear(){}},storage);
  assert.notEqual(saved.get('autocare.session.reset'),first);
});
