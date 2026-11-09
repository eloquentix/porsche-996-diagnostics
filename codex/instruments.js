// 996-inspired instruments. All values retain the existing read-only pdiag source.
function dialSurface(s, c, r, id) {
  const defs=svg('defs',{},s);
  for(const [name,stops] of Object.entries({rim:[['0%','#4d5357'],['22%','#171b1e'],['52%','#080b0d'],['85%','#303539'],['100%','#090c0e']],face:[['0%','#343b40'],['45%','#252b30'],['100%','#181d21']],hub:[['0%','#51595c'],['45%','#2c3336'],['100%','#101517']]})) {
    const g=svg('linearGradient',{id:`${name}-${id}`,x1:'0',y1:'0',x2:name==='hub'?'1':'0',y2:'1'},defs);
    stops.forEach(([offset,color])=>svg('stop',{offset,'stop-color':color},g));
  }
  svg('circle',{cx:c,cy:c,r,fill:`url(#rim-${id})`,stroke:'#090b0d','stroke-width':2},s);
  svg('circle',{cx:c,cy:c,r:r-5,fill:'none',stroke:'#747d80','stroke-opacity':'.24','stroke-width':1},s);
  svg('circle',{cx:c,cy:c,r:r-10,fill:'#090c0e',stroke:'#020405','stroke-width':3},s);
  svg('circle',{cx:c,cy:c,r:r-15,fill:`url(#face-${id})`,stroke:'#454c50','stroke-width':1.2},s);
  svg('path',{d:`M ${c-r+19} ${c} A ${r-19} ${r-19} 0 0 1 ${c+r-19} ${c}`,fill:'none',stroke:'#c6d0d2','stroke-opacity':'.05','stroke-width':3},s);
}
function dialText(s,text,x,y,cls,extra={}){const t=svg('text',{x,y,'text-anchor':'middle',class:cls,...extra},s);t.textContent=text;return t}
function needleShape(s,c,length,id){
  const g=svg('g',{},s);
  svg('path',{d:`M${c-3} ${c+12} L${c-3.3} ${c-18} L${c-.8} ${c-length} Q${c} ${c-length-3} ${c+.8} ${c-length} L${c+3.3} ${c-18} L${c+3} ${c+12}Z`,class:'t-needle'},g);
  svg('circle',{cx:c,cy:c,r:id==='tach'?18:13,fill:`url(#hub-${id})`,stroke:'#0d1113','stroke-width':1.5},s);
  svg('path',{d:`M${c-11} ${c-7} Q${c} ${c-18} ${c+10} ${c-8}`,fill:'none',stroke:'#80898c','stroke-opacity':'.2','stroke-width':1},s);
  return g;
}
function buildTach(){
  const s=$('#tach');s.replaceChildren();dialSurface(s,200,197,'tach');
  const p=(v,r)=>{const a=(-115+v/8000*230)*Math.PI/180;return[200+r*Math.sin(a),200-r*Math.cos(a)]};
  const [x0,y0]=p(REDLINE,166),[x1,y1]=p(8000,166);
  redArc=svg('path',{d:`M${x0} ${y0} A166 166 0 0 1 ${x1} ${y1}`,class:'t-red'},s);
  for(let v=0;v<=8000;v+=200){
    const major=v%1000===0;const [x,y]=p(v,166),[xx,yy]=p(v,major?152:159);
    svg('line',{x1:x,y1:y,x2:xx,y2:yy,class:'t-tick','stroke-width':major?4:2,style:v>=REDLINE?'stroke:#e95b41':''},s);
    if(major&&v>0&&v<8000){const [tx,ty]=p(v,131);dialText(s,v/1000,tx,ty+10,'t-num',{'textLength':v===1?17:29,lengthAdjust:'spacingAndGlyphs'});}
  }
  dialText(s,'targa',200,157,'t-x',{style:'font:italic 23px Georgia;fill:#aeb8b7;letter-spacing:-1px;opacity:.75'});
  dialText(s,'1/MIN × 1000',200,241,'t-x');
  svg('path',{d:'M 75 286 Q 200 216 325 286 Q 310 351 200 357 Q 90 351 75 286 Z',fill:'#080e11',stroke:'#111719','stroke-width':7},s);
  svg('path',{d:'M 79 287 Q 200 224 321 287 Q 306 346 200 351 Q 94 346 79 287 Z',fill:'#182322',stroke:'#40504b','stroke-opacity':'.45','stroke-width':1.2},s);
  dialText(s,units==='us'?'MPH':'KM/H',140,296,'t-x',{id:'digital-unit',style:'fill:#e5a06a;font-size:12px;font-style:italic'});
  svg('g',{id:'digital-speed',class:'seven-display',transform:'translate(175 262)'},s);
  const bands=svg('g',{id:'bands'},s);drawBands(bands,overRev?.ranges??defaultRanges());
  needle=needleShape(s,200,163,'tach');setNeedle(shownRpm);digitalSpeed(null);
}
function setNeedle(rpm){needle.setAttribute('transform',`rotate(${-115+Math.min(Math.max(rpm,0),8000)/8000*230} 200 200)`);redArc.classList.toggle('hot',rpm>=REDLINE-150)}
const segments=['M4 0H20L17 3H6Z','M21 1L19 16L16 14L18 4Z','M19 18L17 33L14 30L16 20Z','M3 34H16L13 31H5Z','M1 18L4 20L3 30L0 33Z','M3 1L6 4L5 14L1 16Z','M5 15H16L18 17L15 19H4L2 17Z'];
const litSegments=['012345','12','01346','01236','1256','02356','023456','012','0123456','012356'];
let lastDigital='';
function digitalSpeed(v){
  const box=$('#digital-speed');if(!box)return;
  const str=v==null?'---':String(Math.min(999,Math.max(0,Math.round(v)))).padStart(3,' ');
  if(str===lastDigital&&box.childNodes.length)return;
  lastDigital=str;
  // Build segments once; each frame only changes the segments that changed.
  if(!box.childNodes.length){
    for(let i=0;i<3;i++){
      const g=svg('g',{transform:`translate(${i*27} 0)`},box);
      segments.forEach(d=>svg('path',{d,fill:'#f3a366',opacity:'.045'},g));
    }
  }
  [...str].forEach((n,i)=>{
    const active=n==='-'?'6':n===' '?'':litSegments[Number(n)];
    [...box.childNodes[i].childNodes].forEach((path,j)=>{
      const opacity=active?.includes(String(j))?'1':'.045';
      if(path.getAttribute('opacity')!==opacity)path.setAttribute('opacity',opacity);
    });
  });
  box.setAttribute('aria-label',v==null?'Speed unavailable':`${Math.round(v)} ${units==='us'?'mph':'km/h'}`);
}
function buildDial(d){
  const s=$(`#${d.id}`);s.replaceChildren();const C=150,id=d.id;dialSurface(s,C,147,id);
  const speed=d.key==='speed',small=d.key==='intake_temp'||d.key==='engine_load';
  const [lo,hi,major,minor]=speed?(units==='us'?[0,200,25,5]:[0,300,50,10]):d.range();
  const sweep=speed?250:240,half=sweep/2;
  const point=(v,r)=>{const a=(-half+(v-lo)/(hi-lo)*sweep)*Math.PI/180;return[C+r*Math.sin(a),C-r*Math.cos(a)]};
  for(let v=lo;v<=hi+1e-6;v+=minor){const big=Math.abs((v-lo)/major-Math.round((v-lo)/major))<1e-6;const [x,y]=point(v,119),[xx,yy]=point(v,big?109:114);svg('line',{x1:x,y1:y,x2:xx,y2:yy,class:'t-tick','stroke-width':big?2.8:1.5},s);if(big&&(!speed||v<hi)){const[tx,ty]=point(v,speed?96:91);dialText(s,Math.round(v),tx,ty+6,'d-num',{style:small?'font-size:17px':'font-size:18px'});}}
  if(d.hot){const[x,y]=point(d.hot(),119),[xx,yy]=point(hi,119);svg('path',{d:`M${x} ${y} A119 119 0 0 1 ${xx} ${yy}`,class:'t-red'},s)}
  dialText(s,d.label.toUpperCase(),small?(d.key==='intake_temp'?C-17:C+17):C,speed?184:183,'d-label',{style:small?'font-size:8px;letter-spacing:1px':''});
  svg('path',{d:'M 65 218 Q150 185 235 218 Q223 261 150 266 Q77 261 65 218 Z',fill:'#111b1b',stroke:'#090e10','stroke-width':4},s);
  const val=dialText(s,'–',C,239,'d-value');dialText(s,d.unit().toUpperCase(),C,254,'d-unit',{style:'fill:#c88b5e;font-size:9px'});
  const n=needleShape(s,C,115,id);
  const st=dialState[id]??{target:null,shown:null};Object.assign(st,{needle:n,val,lo,hi,sweep,C});dialState[id]=st;drawDial(d,st);
}
const baseUpdateDials=updateDials;
updateDials=function(values){
  baseUpdateDials(values);
  $('#digital-unit').textContent=units==='us'?'MPH':'KM/H';
  const missing=[];
  for(const d of DIALS){
    const unavailable=values[d.key]==null;
    $(`#${d.id}`).classList.toggle('unavailable',unavailable);
    $(`#${d.id}`).setAttribute('aria-label',unavailable?`${d.label}: no reading yet`:`${d.label}: ${fmt(d.conv?d.conv(values[d.key]):values[d.key])} ${d.unit()}`);
    if(unavailable)missing.push(d.label.toLowerCase());
  }
  $('#digital-speed').classList.toggle('unavailable',values.speed==null);
  $('#freshness').textContent=missing.length?'Waiting for '+missing.join(', '):'Receiving data';
  lastReceived=Date.now();
};
const baseUnitToggle=unitToggle;
unitToggle=function(){baseUnitToggle();const b=$('#live-note').nextElementSibling;b.style.marginLeft='0';$('#unit-slot').append(b)};
let lastReceived=0;
const baseSetStale=setStale;
setStale=function(on){baseSetStale(on);$('#tach').setAttribute('aria-label',on?'Tachometer, readings stale':'Tachometer');if(on)$('#freshness').textContent='Signal lost · readings held';};
setInterval(()=>{if(liveWanted&&lastReceived&&Date.now()-lastReceived>8000){setStale(true);setLink('err','<strong>Waiting for telemetry.</strong> Last readings are held.')}},2000);
$('#focus-btn').onclick=()=>{const on=document.body.classList.toggle('focus-mode');$('#focus-btn').setAttribute('aria-pressed',on);$('#focus-btn').innerHTML=on?'↙ <span class="focus-label">Exit focus</span>':'⛶ <span class="focus-label">Focus</span>'};
$('#night-btn').onclick=()=>{const on=document.body.classList.toggle('night-mode');$('#night-btn').setAttribute('aria-pressed',on)};
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('focus-mode'))$('#focus-btn').click()});
window.addEventListener('hashchange',()=>{if(location.hash!=='#live'){document.body.classList.remove('focus-mode');$('#focus-btn').setAttribute('aria-pressed','false');$('#focus-btn').innerHTML='⛶ <span class="focus-label">Focus</span>'}});
// Full live readings stay visible below the instruments.
renderAll=function(values){
  lastValues=values;
  const keys=Object.keys(values).sort((a,b)=>(ORDER.indexOf(a)+1||99)-(ORDER.indexOf(b)+1||99)||a.localeCompare(b));
  const body=$('#all');
  if(keys.join()!==allKeys){
    allKeys=keys.join();
    body.replaceChildren(...keys.map(key=>{
      const row=document.createElement('tr'),label=document.createElement('th'),value=document.createElement('td');
      label.scope='row';label.textContent=LABELS[key]??key.replaceAll('_',' ');value.dataset.key=key;
      row.append(label,value);return row;
    }));
  }
  for(const cell of body.querySelectorAll('td[data-key]')){
    const value=showValue(cell.dataset.key,values[cell.dataset.key]);if(cell.textContent!==value)cell.textContent=value;
  }
};
function syncInstrumentControls(){ $('.cockpit-actions').hidden=!!location.hash&&location.hash!=='#live'; }
window.addEventListener('hashchange',syncInstrumentControls);
syncInstrumentControls();
// Preview data is opt-in and always explicitly labelled; live mode never invents data.
const previewMode=new URLSearchParams(location.search).has('demo')||location.protocol==='file:';
let demoTimer;
if(previewMode){
  const profile={code:'996',name:'911 (996)',redline:7200,over_rev_from:[7300,7600,7900,8200,8500,8800]};
  const demoStatus={mode:'mock',car:'996 Targa',connected:true,profile,units:{rpm:'rpm',coolant_temp:'C',intake_temp:'C',speed:'km/h',engine_load:'%',throttle:'%',maf:'g/s',timing_advance:'deg',stft_b1:'%',ltft_b1:'%'}};
  api=async function(path){if(path==='/api/status')return demoStatus;if(path==='/api/ident')return {...demoStatus,vin:null,software:'Design preview',dme_address:'0x11',dme_keybytes:'—'};if(path==='/api/dtcs')return [];if(path==='/api/over-rev')throw Object.assign(new Error('Over-rev history is not available in this design preview.'),{kind:'not_decoded'});throw new Error('Unavailable in preview')};
  renderLink=function(){setLink('sim','<strong>Design preview</strong> · Simulated readings')};
  startLive=function(){liveWanted=true;if(demoTimer)return;const tick=()=>{const t=Date.now()/1700;const values={rpm:2370+Math.sin(t)*120,speed:64,coolant_temp:95,intake_temp:32,engine_load:26+Math.sin(t)*4,throttle:18,maf:11,timing_advance:43.5,stft_b1:3.2,ltft_b1:1.6};targetRpm=values.rpm;setStale(false);renderLink();updateReadouts(values);updateDials(values);renderAll(values);$('#freshness').textContent='Simulated readings'};tick();demoTimer=setInterval(tick,300)};
  stopLive=function(){liveWanted=false;clearInterval(demoTimer);demoTimer=null};
  startDme=function(){$('#dme-body').innerHTML='<div class="state"><h3>Live connection required</h3><p>Raw engine data is available when connected to pdiag.</p></div>'};
}
window.addEventListener('pagehide',()=>{stopLive();stopDme()});
init();
