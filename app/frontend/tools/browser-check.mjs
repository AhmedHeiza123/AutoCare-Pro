/** Local browser comparison against the immutable dist, using a test-only API.
 * Does not open or mutate any installed AutoCare database or service.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {randomBytes,createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import {createServer,preview,build} from 'vite';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const baseline=path.join(root,'recovery/original-dist');
const evidence=path.join(root,'validation/browser');
fs.mkdirSync(path.join(evidence,'images'),{recursive:true});
const permissions=['customers.read','customers.write','vehicles.read','vehicles.write','visits.read','visits.write','users.manage','audit.read','backup.manage','settings.manage','technicians.manage','jobs.override','parts.write','parts.costs','suppliers.write','quotes.write','quotes.approve','billing.read','billing.write','billing.refund','expenses.read','expenses.write','reports.financial','qc.write','delivery.write','warranties.decide'];
const user={id:'00000000-0000-4000-8000-000000000001',username:'recovery-review',full_name:'Recovery Reviewer',role:'admin',role_label:'Administrator',permissions,is_active:true};
const testPassword=randomBytes(24).toString('base64url');
const unexpectedApi=[];const apiMethods=[];
const settings={
  workshop:{name:'Fictional Test Workshop',name_en:'Fictional Test Workshop',phone:'',address:'',email:'',tax_number:''},
  general:{language:'en',theme:'light',working_hours:{open:'08:00',close:'18:00',days:[0,1,2,3,4,5]}},
  finance:{currency:'QAR',default_tax_rate:'0.00',default_labor_rate:'0.00',invoice_prefix:'INV',credit_prefix:'CN',job_prefix:'JOB',number_width:6,payment_methods:[{key:'cash',label:'Cash'}],labor_rates:[]},
  warranty:{default_part_months:0,default_labor_months:0},repair_catalog:{items:[]},demo:true,
};
function json(res,status,body,headers={}){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',...headers});res.end(JSON.stringify(body));}
async function api(req,res){
  const url=new URL(req.url,'http://localhost');const p=url.pathname;
  apiMethods.push({method:req.method,path:p});
  const authed=(req.headers.cookie??'').includes('ac_session=recovery-fixture-only');
  const activeUser=req.headers['x-recovery-user']==='second'?{...user,id:'00000000-0000-4000-8000-000000000004',username:'recovery-second',full_name:'Second Recovery Reviewer'}:user;
  if(p==='/api/auth/me')return json(res,authed?200:401,authed?{user:activeUser,csrf_token:'fixture-csrf-only'}:{error:'unauthenticated',message:'Sign in required'});
  if(p==='/api/auth/setup-needed')return json(res,200,{setup_needed:req.headers['x-recovery-setup']==='true',default_language:'en'});
  if(p==='/api/auth/login'&&req.method==='POST'){
    let text='';for await(const chunk of req)text+=chunk;
    const input=JSON.parse(text);
    if(input.username!==activeUser.username||input.password!==testPassword)return json(res,401,{error:'bad_credentials',message:'Fixture login refused'});
    return json(res,200,{user:activeUser,csrf_token:'fixture-csrf-only'},{'Set-Cookie':'ac_session=recovery-fixture-only; HttpOnly; SameSite=Lax; Path=/'});
  }
  if(p==='/api/auth/logout'&&req.method==='POST')return json(res,200,{ok:true},{'Set-Cookie':'ac_session=; Max-Age=0; Path=/'});
  if(p==='/health')return json(res,200,{status:'ok',version:'test-fixture-only'});
  if(!authed)return json(res,401,{error:'unauthenticated',message:'Sign in required'});
  if(p==='/api/settings')return json(res,200,req.headers['x-recovery-user']==='second'?{...settings,workshop:{...settings.workshop,name:'Second Fictional Workshop'}}:settings);
  if(p==='/api/customers')return json(res,200,{items:[{id:'00000000-0000-4000-8000-000000000002',customer_no:1,full_name:'Example Customer',mobile:'NOT-A-PHONE',is_active:true,customer_type:'individual'}],total:1});
  if(p==='/api/vehicles')return json(res,200,{items:[{id:'00000000-0000-4000-8000-000000000003',plate:'DEMO-001',make:'Example',model:'Test Car',model_year:2026,customer_name:'Example Customer'}],total:1});
  if(['/api/board','/api/invoices','/api/attachments','/api/reports','/api/suppliers','/api/technicians'].includes(p))return json(res,200,[]);
  unexpectedApi.push({method:req.method,path:p});
  return json(res,404,{error:'fixture_missing',message:'No fixture for this route'});
}
function staticServer(){return http.createServer(async(req,res)=>{
  if(req.url.startsWith('/api/')||req.url.startsWith('/health'))return api(req,res);
  const decoded=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  let target=path.resolve(baseline,'.'+decoded);
  if(!target.startsWith(baseline+path.sep)||!fs.existsSync(target)||!fs.statSync(target).isFile())target=path.join(baseline,'index.html');
  const type={'.js':'text/javascript','.css':'text/css','.woff':'font/woff','.woff2':'font/woff2','.html':'text/html'}[path.extname(target)]??'application/octet-stream';
  res.writeHead(200,{'Content-Type':type});fs.createReadStream(target).pipe(res);
});}
const listen=server=>new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',()=>resolve(`http://127.0.0.1:${server.address().port}`));});
const close=server=>new Promise(resolve=>{server.closeAllConnections?.();server.close(()=>resolve());});
const results=[];const external=[];const jsErrors=[];
let browser,dev,built;const baselineServer=staticServer();const apiServer=http.createServer(api);
const previousTarget=process.env.AUTOCARE_API_TARGET;
try{
  const baselineOrigin=await listen(baselineServer);
  const apiOrigin=await listen(apiServer);
  process.env.AUTOCARE_API_TARGET=apiOrigin;
  const configFile=path.join(root,'vite.config.js');
  // Always replace stale/original output from the recovered sources before
  // previewing. This check must not pass merely because an old dist exists.
  await build({root,configFile,logLevel:'warn'});
  const builtHtml=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');
  const builtJs=builtHtml.match(/src="(\/assets\/[^\"]+\.js)"/)?.[1];
  assert.ok(builtJs,'Fresh build did not emit a JavaScript entry');
  const servedJsSha256=createHash('sha256').update(fs.readFileSync(path.join(root,'dist',builtJs.slice(1)))).digest('hex');
  dev=await createServer({root,configFile,server:{port:0,strictPort:true},logLevel:'warn'});await dev.listen();
  built=await preview({root,configFile,preview:{port:0,strictPort:true},logLevel:'warn'});
  const devOrigin=`http://127.0.0.1:${dev.httpServer.address().port}`;
  const builtOrigin=`http://127.0.0.1:${built.httpServer.address().port}`;
  const allowed=new Set([baselineOrigin,apiOrigin,devOrigin,builtOrigin]);
  browser=await chromium.launch({headless:true,...(process.env.AUTOCARE_BROWSER_EXECUTABLE?{executablePath:process.env.AUTOCARE_BROWSER_EXECUTABLE}:{})});
  const cases=[
    {name:'login-en',route:'/login',lang:'en',text:'Log in'},
    {name:'login-ar',route:'/login',lang:'ar',text:'تسجيل الدخول'},
    {name:'setup-en',route:'/login',lang:'en',setup:true,text:'First-time system setup'},
    {name:'home-en',route:'/',lang:'en',auth:true,text:'Recovery Reviewer'},
    {name:'customers-en',route:'/customers',lang:'en',auth:true,text:'Example Customer'},
    {name:'customer-form-en',route:'/customers?new=1',lang:'en',auth:true,text:'Example Customer'},
    {name:'vehicles-ar',route:'/vehicles',lang:'ar',auth:true,text:'DEMO-001'},
    {name:'board-en',route:'/board',lang:'en',auth:true,text:'Workshop board'},
    {name:'reports-en',route:'/reports',lang:'en',auth:true,text:'Reports'},
    {name:'home-mobile-ar',route:'/',lang:'ar',auth:true,mobile:true,text:'Recovery Reviewer'},
    {name:'deep-link-unauth',route:'/jobs/00000000-0000-4000-8000-000000000099',lang:'en',text:'Log in'},
  ];
  async function pageFor(origin,spec){
    const context=await browser.newContext({viewport:spec.mobile?{width:390,height:844}:{width:1440,height:1000},deviceScaleFactor:1,locale:'en-GB',timezoneId:'Asia/Riyadh',extraHTTPHeaders:{'X-Recovery-Setup':String(!!spec.setup)}});
    await context.addInitScript(lang=>{if(!localStorage.getItem('autocare.lang'))localStorage.setItem('autocare.lang',lang);},spec.lang);
    if(spec.auth)await context.addCookies([{name:'ac_session',value:'recovery-fixture-only',url:origin,httpOnly:true,sameSite:'Lax'}]);
    await context.route('**/*',route=>{
      const url=new URL(route.request().url());
      if(!['http:','https:'].includes(url.protocol)||allowed.has(url.origin))return route.continue();
      external.push(url.origin);return route.abort();
    });
    const page=await context.newPage();page.on('pageerror',error=>jsErrors.push({case:spec.name,message:error.message}));
    await page.goto(origin+spec.route,{waitUntil:'networkidle'});
    await page.waitForFunction(text=>document.body.innerText.includes(text),spec.text,{timeout:12000});
    await page.evaluate(()=>document.fonts.ready);
    await page.addStyleTag({content:'* { animation: none !important; transition: none !important; }'});
    return {context,page};
  }
  for(const spec of cases){
    const a=await pageFor(baselineOrigin,spec);const b=await pageFor(builtOrigin,spec);
    try{
      const textA=await a.page.locator('body').innerText();const textB=await b.page.locator('body').innerText();
      assert.equal(textB,textA,`${spec.name}: visible content differs`);
      assert.equal(await b.page.locator('html').getAttribute('dir'),spec.lang==='ar'?'rtl':'ltr');
      if(spec.name==='customer-form-en'){
        assert.ok(await a.page.locator('form input').count()>0,'Original new-customer form did not open');
        assert.ok(await b.page.locator('form input').count()>0,'Recovered new-customer form did not open');
        assert.ok(await b.page.getByRole('button',{name:'Save',exact:true}).count()>0,'New-customer Save control missing');
      }
      const imageA=await a.page.screenshot({path:path.join(evidence,'images',spec.name+'-original.png'),fullPage:true,animations:'disabled',caret:'hide'});
      const imageB=await b.page.screenshot({path:path.join(evidence,'images',spec.name+'-recovered.png'),fullPage:true,animations:'disabled',caret:'hide'});
      assert.equal(imageB.equals(imageA),true,`${spec.name}: screenshot pixels differ`);
      results.push({case:spec.name,visibleTextEqual:true,screenshotEqual:true,language:spec.lang,path:new URL(b.page.url()).pathname});
      console.log('PASS baseline comparison: '+spec.name);
    }finally{await a.context.close();await b.context.close();}
  }
  // Exercise a real HTTP development proxy and actual form behavior, rather
  // than intercepting browser requests or reaching any installed backend.
  const login=await pageFor(devOrigin,{name:'dev-login-flow',route:'/login',lang:'en',text:'Log in'});
  try{
    await login.page.locator('input[autocomplete="username"]').fill(user.username);
    await login.page.locator('input[type="password"]').fill(testPassword);
    await login.page.locator('button[type="submit"]').click();
    await login.page.waitForFunction(()=>document.body.innerText.includes('Recovery Reviewer'),null,{timeout:12000});
    assert.equal(new URL(login.page.url()).pathname,'/');
    await login.page.getByRole('button',{name:'التبديل إلى العربية'}).first().click();
    await login.page.waitForFunction(()=>document.documentElement.dir==='rtl'&&document.body.innerText.includes('Recovery Reviewer'));
    results.push({case:'development-proxy-login-and-language-switch',passed:true});
    const otherTab=await login.context.newPage();
    await otherTab.goto(devOrigin+'/',{waitUntil:'networkidle'});
    await otherTab.waitForFunction(()=>document.body.innerText.includes('Recovery Reviewer'));
    await login.page.evaluate(()=>localStorage.setItem('autocare.reception.draft','PRIVATE_TEST_DRAFT'));
    await login.page.getByRole('button',{name:/Log out|خروج/}).first().click();
    await login.page.locator('input[autocomplete="username"]').waitFor({state:'visible'});
    assert.equal(await login.page.evaluate(()=>localStorage.getItem('autocare.reception.draft')),null,'Private draft survived logout');
    await otherTab.locator('input[autocomplete="username"]').waitFor({state:'visible'});
    await otherTab.close();
    await login.context.setExtraHTTPHeaders({'X-Recovery-Setup':'false','X-Recovery-User':'second'});
    await login.page.locator('input[autocomplete="username"]').fill('recovery-second');
    await login.page.locator('input[type="password"]').fill(testPassword);
    await login.page.locator('button[type="submit"]').click();
    await login.page.waitForFunction(()=>document.body.innerText.includes('Second Recovery Reviewer')&&document.body.innerText.includes('Second Fictional Workshop'));
    results.push({case:'logout-removes-draft-clears-other-tab-and-next-account-loads-fresh-settings',passed:true});
  }finally{await login.context.close();}
  assert.equal(external.length,0,'UI attempted to load an external dependency');
  assert.equal(jsErrors.length,0,JSON.stringify(jsErrors));
  assert.equal(unexpectedApi.length,0,JSON.stringify(unexpectedApi));
  const report={browser:await browser.version(),checkedAt:new Date().toISOString(),mockedApi:true,realDatabaseUsed:false,cases:results,jsErrors,externalRequests:external,unexpectedApi,apiRequests:apiMethods.length,productionBuild:{rebuiltFromRecoveredSource:true,script:builtJs,sha256:servedJsSha256}};
  fs.writeFileSync(path.join(evidence,'report.json'),JSON.stringify(report,null,2)+'\n');
  fs.rmSync(path.join(evidence,'failure.json'),{force:true});
  console.log(JSON.stringify({passed:results.length,apiRequests:apiMethods.length,jsErrors:jsErrors.length,externalRequests:external.length},null,2));
}catch(error){
  fs.writeFileSync(path.join(evidence,'failure.json'),JSON.stringify({message:error.message,completedCases:results,jsErrors,external,unexpectedApi},null,2));
  throw error;
}finally{
  await browser?.close();await dev?.close();if(built)await close(built.httpServer);await close(baselineServer);await close(apiServer);
  if(previousTarget===undefined)delete process.env.AUTOCARE_API_TARGET;else process.env.AUTOCARE_API_TARGET=previousTarget;
}
