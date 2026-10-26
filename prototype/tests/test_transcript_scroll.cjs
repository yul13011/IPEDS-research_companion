/* Run the production controller against deterministic browser event/layout doubles. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync(require('node:path').join(__dirname,'../transcript_scroll.js'),'utf8');

function browser() {
  const events={},frames=[],mutations=[],resizes=[];
  const element={isConnected:true,scrollHeight:2000,clientHeight:400,scrollTop:0,firstElementChild:{},
    addEventListener:(name,fn)=>events[name]=fn,removeEventListener:()=>{},
    getBoundingClientRect:()=>({right:1000})};
  const window={addEventListener:()=>{}};
  const sandbox={window,document:{body:{},querySelector:()=>element},
    requestAnimationFrame:fn=>(frames.push(fn),frames.length),
    MutationObserver:class{constructor(fn){mutations.push(fn)} observe(){}},
    ResizeObserver:class{constructor(fn){resizes.push(fn)} observe(){} disconnect(){}}};
  vm.runInNewContext(code,sandbox);
  const flush=()=>{for(const fn of frames.splice(0))fn()};
  const change=()=>{mutations.forEach(fn=>fn());flush()};
  const update=(request,editing=false)=>{window.ipedsTranscriptScroll.update({request,editing});flush()};
  return {element,events,update,change,flush,resizes};
}

test('new submission follows from old messages; pending and completion keep position at bottom',()=>{
  const b=browser();b.update(0);assert.equal(b.element.scrollTop,2000);
  b.events.wheel({deltaY:-100});b.element.scrollTop=250;b.events.scroll();b.change();
  assert.equal(b.element.scrollTop,250);
  b.update(1);assert.equal(b.element.scrollTop,2000);
  b.element.scrollHeight=2400;b.change();assert.equal(b.element.scrollTop,2400);
  b.update(1);b.element.scrollHeight=2800;b.change();assert.equal(b.element.scrollTop,2800);
});

test('reading older messages during a query is preserved when answer and late chart arrive',()=>{
  const b=browser();b.update(1);
  b.events.wheel({deltaY:-100});b.element.scrollTop=300;b.events.scroll();
  b.element.scrollHeight=3000;b.update(1);b.change();
  b.resizes.forEach(fn=>fn());b.flush();assert.equal(b.element.scrollTop,300);
  b.update(2);assert.equal(b.element.scrollTop,3000);
});

test('scrollbar reading, return to bottom, menu resizing and formatting do not fight the user',()=>{
  const b=browser();b.update(0);
  b.events.pointerdown({clientX:995});b.element.scrollTop=100;b.events.scroll();b.change();
  assert.equal(b.element.scrollTop,100);
  b.element.clientHeight=600;b.resizes.forEach(fn=>fn());b.flush();assert.equal(b.element.scrollTop,100);
  b.element.scrollTop=1400;b.events.scroll();b.element.scrollHeight=2500;b.change();
  assert.equal(b.element.scrollTop,2500);
  b.update(0,true);b.element.scrollTop=200;b.element.scrollHeight=2900;b.change();assert.equal(b.element.scrollTop,200);
  b.update(0,false);assert.equal(b.element.scrollTop,200);
  b.update(1);assert.equal(b.element.scrollTop,2900);
});
