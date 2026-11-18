/** Reconstruct editable compiled JS from the immutable bundle. Explicit use only:
 * this overwrites src/recovered/*.js, so do not run it over later manual edits.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {parse} from '@babel/parser';
import {generate} from '@babel/generator';
import traverse from '@babel/traverse';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
if(fs.existsSync(path.join(root,'recovery/security-patches.json')))throw Error('Recovery would overwrite reviewed security fixes. Use the preserved baseline in a separate working copy, then reapply/retest the patches.');
const baseline=path.join(root,'recovery/original-dist/assets');
const jsName=fs.readdirSync(baseline).find(n=>n.endsWith('.js'));
const cssName=fs.readdirSync(baseline).find(n=>n.endsWith('.css'));
const original=fs.readFileSync(path.join(baseline,jsName),'utf8');
const ast=parse(original,{sourceType:'module'});
const nodes=ast.program.body;
const localeNode=nodes.find(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.type==='Identifier'&&d.id.name==='bu'));
const appNode=nodes.find(n=>n.type==='ClassDeclaration'&&n.id?.name==='Sr');
if(!localeNode||!appNode)throw Error('Unexpected bundle shape: inspect boundaries before recovery');
const names=['runtime','localization','application'];
const group=pos=>pos<localeNode.start?0:pos<appNode.start?1:2;
const imports=names.map(()=>new Map());
const exports=names.map(()=>new Set());
const routes=[];
const apiPatterns=new Set();
traverse(ast,{
  Program(p){
    for(const [name,binding] of Object.entries(p.scope.bindings)){
      const source=group(binding.path.node.start);
      for(const ref of binding.referencePaths){
        const dest=group(ref.node.start);
        if(source===dest)continue;
        if(source>dest)throw Error(`Backward dependency for ${name}; unsafe module boundary`);
        const set=imports[dest].get(source)??new Set();set.add(name);imports[dest].set(source,set);exports[source].add(name);
      }
      for(const write of binding.constantViolations)if(group(write.node.start)!==source)throw Error(`Cross-module mutation of ${name}`);
    }
  },
  ObjectExpression(p){
    const props=p.node.properties.filter(n=>n.type==='ObjectProperty');
    const route=props.find(n=>n.key.name==='path'&&n.value.type==='StringLiteral');
    const element=props.find(n=>n.key.name==='element'&&n.value.type==='CallExpression');
    if(route&&element&&element.value.arguments[0]?.type==='Identifier')routes.push({path:route.value.value,symbol:element.value.arguments[0].name});
  },
  StringLiteral(p){if(p.node.value.startsWith('/api/'))apiPatterns.add(p.node.value);},
  TemplateLiteral(p){const text=p.node.quasis.map((q,i)=>q.value.cooked+(i<p.node.expressions.length?'{...}':'')).join('');if(text.startsWith('/api/'))apiPatterns.add(text);},
});
const sections=names.map(()=>[]);
for(const node of nodes){
  if(node.type==='FunctionDeclaration'&&node.id){
    const related=routes.filter(r=>r.symbol===node.id.name);
    if(related.length)node.leadingComments=[...(node.leadingComments??[]),{type:'CommentLine',value:` Recovered route component for ${related.map(r=>r.path).join(', ')}; original filename/name unknown.`}];
  }
  sections[group(node.start)].push(node);
}
fs.mkdirSync(path.join(root,'src/recovered'),{recursive:true});
for(let index=0;index<names.length;index++){
  const module=parse('',{sourceType:'module'});
  const prefix=[];
  for(const [source,symbols] of imports[index])prefix.push(...parse(`import { ${[...symbols].join(', ')} } from './${names[source]}.js';`,{sourceType:'module'}).program.body);
  const suffix=exports[index].size?parse(`export { ${[...exports[index]].join(', ')} };`,{sourceType:'module',allowUndeclaredExports:true}).program.body:[];
  module.program.body=[...prefix,...sections[index],...suffix];
  const code=generate(module,{comments:true,compact:false,minified:false,jsescOption:{minimal:true}}).code;
  const header=`// Recovered compiled JavaScript. Original JSX/types/filenames are unavailable.\n// Do not treat inferred file boundaries as the original authoring architecture.\n`;
  fs.writeFileSync(path.join(root,`src/recovered/${names[index]}.js`),header+code+'\n');
}
fs.mkdirSync(path.join(root,'src/styles'),{recursive:true});
fs.copyFileSync(path.join(baseline,cssName),path.join(root,'src/styles/recovered.css'));
fs.mkdirSync(path.join(root,'public/assets'),{recursive:true});
const fonts=fs.readdirSync(baseline).filter(n=>/\.woff2?$/.test(n));
for(const name of fonts)fs.copyFileSync(path.join(baseline,name),path.join(root,'public/assets',name));
const hash=buffer=>crypto.createHash('sha256').update(buffer).digest('hex');
const manifest={kind:'compiled-JavaScript recovery; not original source',baseline:{js:jsName,jsSha256:hash(fs.readFileSync(path.join(baseline,jsName))),css:cssName,cssSha256:hash(fs.readFileSync(path.join(baseline,cssName)))},originalStatements:nodes.length,fonts:fonts.length,modules:names.map((name,i)=>({name,originalStatements:sections[i].length,exports:[...exports[i]],imports:Object.fromEntries([...imports[i]].map(([g,s])=>[names[g],[...s]]))})),routes,apiPatterns:[...apiPatterns].sort(),embeddedLicenseNotices:ast.comments.filter(c=>/@license|licensed under/i.test(c.value)).length};
fs.writeFileSync(path.join(root,'recovery/manifest.json'),JSON.stringify(manifest,null,2)+'\n');
fs.writeFileSync(path.join(root,'recovery/EMBEDDED-NOTICES.txt'),ast.comments.filter(c=>/@license|licensed under/i.test(c.value)).map(c=>'/*'+c.value+'*/').join('\n\n')+'\n');
console.log(JSON.stringify({originalStatements:nodes.length,moduleStatements:sections.map(s=>s.length),fonts:fonts.length,routes:routes.length,apiPatterns:apiPatterns.size},null,2));
