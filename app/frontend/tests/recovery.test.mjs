import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import test from 'node:test';
import {parse} from '@babel/parser';
import traverse from '@babel/traverse';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const baseline=path.join(root,'recovery/original-dist/assets');
const originalJs=fs.readdirSync(baseline).find(n=>n.endsWith('.js'));
const originalCss=fs.readdirSync(baseline).find(n=>n.endsWith('.css'));
const ignored=new Set(['start','end','loc','extra','leadingComments','trailingComments','innerComments','comments','tokens','errors']);
function canonical(value){
  if(Array.isArray(value))return value.map(canonical);
  // Babel inserts braces around a lone nested if to avoid dangling-else
  // ambiguity; this introduces no direct lexical declaration or new behavior.
  if(value?.type==='BlockStatement'&&value.body.length===1&&value.body[0].type==='IfStatement'&&!value.directives?.length)return canonical(value.body[0]);
  if(value?.type==='LogicalExpression'){
    const operands=[];
    const flatten=n=>{if(n.type==='LogicalExpression'&&n.operator===value.operator){flatten(n.left);flatten(n.right);}else operands.push(canonical(n));};
    flatten(value);
    return {type:'LogicalExpression',operator:value.operator,operands};
  }
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).filter(([k])=>!ignored.has(k)).map(([k,v])=>[k,canonical(v)]));
  return value;
}
const parseModule=s=>parse(s,{sourceType:'module'}).program;
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');

test('recovery retains original statements except explicitly hash-pinned changes',()=>{
  const originalSource=fs.readFileSync(path.join(baseline,originalJs),'utf8');
  const originalBody=parseModule(originalSource).body;
  const expected=canonical(originalBody);
  const patches=JSON.parse(fs.readFileSync(path.join(root,'recovery/security-patches.json'),'utf8'));
  const catalog=JSON.parse(fs.readFileSync(path.join(root,'recovery/catalog-patches.json'),'utf8'));
  const find=(body,{symbol,type})=>body.find(n=>n.type===type&&(
    n.id?.name===symbol || n.declarations?.some(entry=>entry.id.name===symbol)
  ));
  const recovered=[];
  for(const name of ['runtime','localization','application']){
    const file=path.join(root,`src/recovered/${name}.js`);
    assert.ok(fs.existsSync(file),`Missing recovered ${name} module`);
    const ast=parseModule(fs.readFileSync(file,'utf8'));
    const source=fs.readFileSync(file,'utf8');
    const tracked=[...patches.modifiedFunctions.map(patch=>({...patch,type:'FunctionDeclaration'})),...catalog.statements];
    for(const patch of tracked){
      if(patch.module!==name)continue;
      const old=find(originalBody,patch);
      const current=find(ast.body,patch);
      assert.ok(current,`Pinned statement missing: ${patch.symbol}`);
      assert.equal(hash(source.slice(current.start,current.end)),patch.patchedSha256,`Reviewed change differs: ${patch.symbol}`);
      if(patch.originalSha256){
        assert.ok(old,`Original statement missing: ${patch.symbol}`);
        assert.equal(hash(originalSource.slice(old.start,old.end)),patch.originalSha256,`Original statement differs: ${patch.symbol}`);
        ast.body[ast.body.indexOf(current)]=old;
      }else{
        assert.equal(old,undefined,`Added statement already existed: ${patch.symbol}`);
        ast.body.splice(ast.body.indexOf(current),1);
      }
    }
    recovered.push(...ast.body.filter(n=>!['ImportDeclaration','ExportNamedDeclaration'].includes(n.type)));
  }
  const actual=canonical(recovered);
  function firstDifference(a,b,at='statements'){
    if(typeof a!==typeof b||a===null||b===null)return a===b?null:at;
    if(typeof a!=='object')return a===b?null:at+': '+String(a)+' vs '+String(b);
    const keys=[...new Set([...Object.keys(a),...Object.keys(b)])].sort();
    for(const key of keys){const diff=firstDifference(a[key],b[key],at+'.'+key);if(diff)return diff;}
    return null;
  }
  // A bounded diagnostic prevents an AST mismatch from printing a megabyte diff.
  assert.equal(firstDifference(actual,expected),null);
});

test('compiled CSS and all 18 font assets survive recovery byte for byte',()=>{
  const css=path.join(root,'src/styles/recovered.css');
  assert.ok(fs.existsSync(css),'Recovered stylesheet is missing');
  assert.equal(hash(fs.readFileSync(css)),hash(fs.readFileSync(path.join(baseline,originalCss))));
  const fonts=fs.readdirSync(baseline).filter(n=>/\.woff2?$/.test(n));
  assert.equal(fonts.length,18);
  for(const name of fonts)assert.equal(hash(fs.readFileSync(path.join(root,'public/assets',name))),hash(fs.readFileSync(path.join(baseline,name))),name);
});

test('all embedded license notices are retained in the reconstructed JavaScript',()=>{
  const normalize=s=>s.replace(/\s+/g,' ').trim();
  const expected=parse(fs.readFileSync(path.join(baseline,originalJs),'utf8'),{sourceType:'module'}).comments.map(c=>normalize(c.value));
  const actual=['runtime','localization','application'].flatMap(n=>{
    const file=path.join(root,`src/recovered/${n}.js`);assert.ok(fs.existsSync(file),'Recovered module is missing');
    return parse(fs.readFileSync(file,'utf8'),{sourceType:'module'}).comments.map(c=>normalize(c.value));
  });
  for(const comment of expected)assert.ok(actual.includes(comment),'A bundled license/comment was lost');
});

test('module imports resolve and introduce no new unbound global identifiers',()=>{
  const original=parse(fs.readFileSync(path.join(baseline,originalJs),'utf8'),{sourceType:'module'});
  const unbound=ast=>{
    const names=new Set();
    traverse(ast,{ReferencedIdentifier(p){if(!p.scope.getBinding(p.node.name))names.add(p.node.name);}});
    return names;
  };
  const permitted=unbound(original);
  const modules=Object.fromEntries(['runtime','localization','application'].map(name=>[name,parse(fs.readFileSync(path.join(root,`src/recovered/${name}.js`),'utf8'),{sourceType:'module'})]));
  modules['session-privacy']=parse(fs.readFileSync(path.join(root,'src/security/session-privacy.js'),'utf8'),{sourceType:'module'});
  for(const [name,ast] of Object.entries(modules)){
    assert.deepEqual([...unbound(ast)].filter(n=>!permitted.has(n)),[],`${name}: new unbound identifiers`);
    for(const entry of ast.program.body.filter(n=>n.type==='ImportDeclaration')){
      const source=modules[path.basename(entry.source.value,'.js')];assert.ok(source,'Unknown recovery import');
      const exported=new Set(source.program.body.filter(n=>n.type==='ExportNamedDeclaration').flatMap(n=>[...n.specifiers.map(s=>s.exported.name),...(n.declaration?.id?[n.declaration.id.name]:[])]));
      for(const spec of entry.specifiers)assert.ok(exported.has(spec.imported.name),`${name}: unresolved import ${spec.imported.name}`);
    }
  }
  // Confirm this guard detects a missing import even on an unvisited screen.
  const broken=parse(fs.readFileSync(path.join(root,'src/recovered/application.js'),'utf8'),{sourceType:'module'});
  for(const entry of broken.program.body.filter(n=>n.type==='ImportDeclaration'))entry.specifiers=entry.specifiers.filter(s=>s.local.name!=='w');
  assert.ok(unbound(broken).has('w'),'Missing React binding was not detected');
});
