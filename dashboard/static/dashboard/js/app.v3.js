(function(){
  const navToggle=document.querySelector('#navToggle'), mainNav=document.querySelector('#mainNav');
  if(navToggle&&mainNav){navToggle.addEventListener('click',()=>{const open=mainNav.classList.toggle('mobile-open');navToggle.setAttribute('aria-expanded',open?'true':'false');});}

  document.querySelectorAll('.dd-trigger').forEach(btn=>btn.addEventListener('click',e=>{e.stopPropagation();const dd=btn.closest('.dd');document.querySelectorAll('.dd.is-open').forEach(x=>{if(x!==dd)x.classList.remove('is-open')});dd&&dd.classList.toggle('is-open');}));
  document.addEventListener('click',e=>{if(!e.target.closest('.dd'))document.querySelectorAll('.dd.is-open').forEach(x=>x.classList.remove('is-open'));});

  const upi=document.querySelector('#umbrellaProgramInput'), uph=document.querySelector('#umbrellaProgramId'), dl=document.querySelector('#programSuggestions');
  if(upi&&uph&&dl){const syncProgram=()=>{const hit=[...dl.options].find(o=>o.value===upi.value);uph.value=hit?hit.dataset.id:'';};upi.addEventListener('input',syncProgram);upi.addEventListener('change',syncProgram);}

  document.querySelectorAll('[data-toggle]').forEach(cb=>{const sel=cb.dataset.toggle, box=document.querySelector(sel);const sync=()=>box&&box.classList.toggle('hidden',!cb.checked);cb.addEventListener('change',sync);sync();});

  document.addEventListener('click',e=>{
    const rem=e.target.closest('[data-remove]');
    if(rem){const card=rem.closest('.activity-card,.project-card,.field-entry');if(card){card.animate([{opacity:1,transform:'scale(1)'},{opacity:0,transform:'scale(.98)'}],{duration:130}).onfinish=()=>card.remove();}}
    const add=e.target.closest('[data-add-activity]');
    if(add){const host=document.querySelector(add.dataset.addActivity),tpl=document.querySelector('#activityTemplate');if(host&&tpl){const n=host.querySelectorAll('.activity-card').length+1;host.insertAdjacentHTML('beforeend',tpl.innerHTML.replaceAll('__N__',n));const el=host.lastElementChild;el&&el.animate([{opacity:0,transform:'translateY(8px)'},{opacity:1,transform:'none'}],{duration:180});}}
    const nested=e.target.closest('[data-add-nested-activity]');
    if(nested){const host=nested.closest('.nested-activities'),prefix=host.dataset.prefix,n=host.querySelectorAll('.activity-card').length+1;const html=`<div class="activity-card compact"><div class="activity-head"><b>Activity ${n}</b><button type="button" class="icon danger-text" data-remove>Remove</button></div><div class="formgrid three"><label>Title<input name="${prefix}activity_title[]"></label><label>Date<input type="date" name="${prefix}activity_date[]"></label><label>Time<input type="time" name="${prefix}activity_time[]"></label><label>Venue<input name="${prefix}activity_venue[]"></label><label>Activity Leader<input name="${prefix}activity_leader[]"></label><label>Budget<input type="number" min="0" step="0.01" name="${prefix}activity_budget[]"></label></div><div class="formgrid three"><label>Topics<textarea name="${prefix}activity_topics[]" rows="2"></textarea></label><label>Objectives<textarea name="${prefix}activity_objectives[]" rows="2"></textarea></label><label>Learning Outcomes<textarea name="${prefix}activity_outcomes[]" rows="2"></textarea></label></div></div>`;nested.insertAdjacentHTML('beforebegin',html);}
  });

  const addProject=document.querySelector('#addProject'),projects=document.querySelector('#projects'),pt=document.querySelector('#projectTemplate');let pIndex=0;
  if(addProject&&projects&&pt){const add=()=>{pIndex++;projects.insertAdjacentHTML('beforeend',pt.innerHTML.replaceAll('__IDX__',pIndex));const el=projects.lastElementChild;el&&el.animate([{opacity:0,transform:'translateY(10px)'},{opacity:1,transform:'none'}],{duration:180});};addProject.addEventListener('click',add);add();}

  const addField=document.querySelector('#addFieldEntry'),fieldHost=document.querySelector('#fieldEntries'),fieldTpl=document.querySelector('#fieldEntryTemplate');
  if(addField&&fieldHost&&fieldTpl)addField.addEventListener('click',()=>{fieldHost.insertAdjacentHTML('beforeend',fieldTpl.innerHTML);const el=fieldHost.lastElementChild;el&&el.animate([{opacity:0,transform:'translateY(8px)'},{opacity:1,transform:'none'}],{duration:180});});

  document.querySelectorAll('.card,.stat-card').forEach((el,i)=>{if(i<18)el.animate([{opacity:0,transform:'translateY(5px)'},{opacity:1,transform:'none'}],{duration:220,delay:Math.min(i*18,160),fill:'both'});});
})();
