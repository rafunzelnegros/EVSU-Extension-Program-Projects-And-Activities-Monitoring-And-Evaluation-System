(function(){
  const qs=(s,r=document)=>r.querySelector(s), qsa=(s,r=document)=>[...r.querySelectorAll(s)];

  const navToggle=qs('#navToggle'), mainNav=qs('#mainNav');
  if(navToggle&&mainNav){navToggle.addEventListener('click',()=>{const open=mainNav.classList.toggle('mobile-open');navToggle.setAttribute('aria-expanded',open?'true':'false');});}

  qsa('.dd-trigger').forEach(btn=>btn.addEventListener('click',e=>{e.stopPropagation();const dd=btn.closest('.dd');qsa('.dd.is-open').forEach(x=>{if(x!==dd)x.classList.remove('is-open')});dd&&dd.classList.toggle('is-open');}));
  document.addEventListener('click',e=>{if(!e.target.closest('.dd'))qsa('.dd.is-open').forEach(x=>x.classList.remove('is-open'));});

  const upi=qs('#umbrellaProgramInput'), uph=qs('#umbrellaProgramId'), dl=qs('#programSuggestions');
  if(upi&&uph&&dl){const syncProgram=()=>{const hit=[...dl.options].find(o=>o.value===upi.value);uph.value=hit?hit.dataset.id:'';};upi.addEventListener('input',syncProgram);upi.addEventListener('change',syncProgram);}

  function initToggles(root=document){
    qsa('[data-toggle]',root).forEach(cb=>{
      if(cb.dataset.toggleReady)return;
      cb.dataset.toggleReady='1';
      const sync=()=>{const box=qs(cb.dataset.toggle);if(box)box.classList.toggle('hidden',!cb.checked);};
      cb.addEventListener('change',sync);sync();
    });
  }
  initToggles();

  document.addEventListener('click',e=>{
    const lineRemove=e.target.closest('[data-remove-line]');
    if(lineRemove){const host=lineRemove.closest('.line-repeater');const line=lineRemove.closest('.line-input');if(host&&line&&host.querySelectorAll('.line-input').length>1)line.remove();else if(line)qs('input',line).value='';return;}

    const addLine=e.target.closest('[data-add-line]');
    if(addLine){
      const host=qs(addLine.dataset.addLine);
      if(host){const name=addLine.dataset.lineName||'item[]',placeholder=addLine.dataset.placeholder||'Input value';host.insertAdjacentHTML('beforeend',`<div class="line-input"><input name="${name}" placeholder="${placeholder}"><button type="button" class="line-remove" data-remove-line aria-label="Remove">×</button></div>`);const input=host.lastElementChild&&qs('input',host.lastElementChild);if(input)input.focus();}
      return;
    }

    const rem=e.target.closest('[data-remove]');
    if(rem){const card=rem.closest('.activity-card,.project-card');if(card){card.animate([{opacity:1,transform:'scale(1)'},{opacity:0,transform:'scale(.985)'}],{duration:130}).onfinish=()=>card.remove();}return;}

    const add=e.target.closest('[data-add-activity]');
    if(add){const host=qs(add.dataset.addActivity),tpl=qs('#activityTemplate');if(host&&tpl){const n=host.querySelectorAll('.activity-card').length+1;host.insertAdjacentHTML('beforeend',tpl.innerHTML.replaceAll('__N__',n));const el=host.lastElementChild;el&&el.animate([{opacity:0,transform:'translateY(8px)'},{opacity:1,transform:'none'}],{duration:180});}return;}

    const nested=e.target.closest('[data-add-nested-activity]');
    if(nested){const host=nested.closest('.nested-activities'),prefix=host.dataset.prefix,n=host.querySelectorAll('.activity-card').length+1;const html=`<div class="activity-card compact"><div class="activity-head"><b>Activity ${n}</b><button type="button" class="icon danger-text" data-remove>Remove</button></div><div class="formgrid three"><label>Title<input name="${prefix}activity_title[]"></label><label>Date<input type="date" name="${prefix}activity_date[]"></label><label>Time<input type="time" name="${prefix}activity_time[]"></label><label>Venue<input name="${prefix}activity_venue[]"></label><label>Activity Leader<input name="${prefix}activity_leader[]"></label><label>Budget<input type="number" min="0" step="0.01" name="${prefix}activity_budget[]"></label></div><div class="formgrid three"><label>Topics<textarea name="${prefix}activity_topics[]" rows="2"></textarea></label><label>Objectives<textarea name="${prefix}activity_objectives[]" rows="2"></textarea></label><label>Learning Outcomes<textarea name="${prefix}activity_outcomes[]" rows="2"></textarea></label></div></div>`;nested.insertAdjacentHTML('beforebegin',html);return;}
  });

  const addProject=qs('#addProject'),projects=qs('#projects'),pt=qs('#projectTemplate');let pIndex=0;
  if(addProject&&projects&&pt){const add=()=>{pIndex++;projects.insertAdjacentHTML('beforeend',pt.innerHTML.replaceAll('__IDX__',pIndex));const el=projects.lastElementChild;if(el){initToggles(el);el.animate([{opacity:0,transform:'translateY(10px)'},{opacity:1,transform:'none'}],{duration:180});}};addProject.addEventListener('click',add);add();}

  function syncReschedule(select){
    const target=qs(select.dataset.rescheduleTarget);if(!target)return;
    const show=select.value==='RESCHEDULED';target.classList.toggle('hidden',!show);
    const input=qs('input[type="date"]',target);if(input){input.required=show&&!select.disabled;if(!show)input.value='';}
  }
  qsa('.result-select').forEach(sel=>{sel.addEventListener('change',()=>syncReschedule(sel));syncReschedule(sel);});

  // Quarterly Monitoring Report project/status behavior.
  const qmrMetaEl=qs('#qmrProjectMeta'), qmrProject=qs('#qmrProject');
  if(qmrMetaEl&&qmrProject){
    let meta={};try{meta=JSON.parse(qmrMetaEl.textContent||'{}');}catch(e){meta={};}
    const status=qs('#id_project_status'), start=qs('#id_period_start'), end=qs('#id_period_end'), location=qs('#id_location'), funding=qs('#id_funding_source'), cost=qs('#id_total_project_cost');
    const ongoing=qs('#ongoingFields'), inactive=qs('#inactiveFields'), terminated=qs('#terminatedFields'), locked=qs('#terminationLocked'), termField=qs('#terminationDateField'), termInput=qs('#id_date_of_termination'), note=qs('#projectRuleNote');

    const selectedMeta=()=>meta[String(qmrProject.value)]||{};
    const syncStatus=()=>{
      const value=status?status.value:'';
      if(ongoing)ongoing.classList.toggle('hidden',value!=='ONGOING');
      if(inactive)inactive.classList.toggle('hidden',value!=='INACTIVE');
      if(terminated)terminated.classList.toggle('hidden',value!=='TERMINATED');
      if(value==='TERMINATED'){
        const m=selectedMeta(),eligible=!!m.termination_eligible;
        if(locked)locked.classList.toggle('hidden',eligible);
        if(termField)termField.classList.toggle('hidden',!eligible);
        if(termInput){termInput.disabled=!eligible;termInput.required=eligible;}
      } else if(termInput){termInput.required=false;}
    };

    const syncProject=()=>{
      const m=selectedMeta();
      if(start)start.value=m.start||'';if(end)end.value=m.end||'';
      if(location&&m.location)location.value=m.location;if(funding&&m.funding)funding.value=m.funding;if(cost&&m.cost)cost.value=m.cost;
      const termOption=status&&qs('option[value="TERMINATED"]',status);if(termOption)termOption.disabled=!m.termination_eligible;
      if(note){
        if(m.auto_inactive){note.innerHTML=`<b>System status rule:</b> This Project currently meets the automatic Inactive rule (${m.not_conducted||0} monitored Activities are Not Conducted after the Project End Date).`;note.classList.remove('hidden');if(status&&!status.value)status.value='INACTIVE';}
        else if(m.completed){note.innerHTML='<b>Project activity monitoring:</b> Approved Activities are currently recorded as completed.';note.classList.remove('hidden');}
        else note.classList.add('hidden');
      }
      syncStatus();
    };
    qmrProject.addEventListener('change',syncProject);if(status)status.addEventListener('change',syncStatus);syncProject();syncStatus();
  }

  qsa('.card,.reference-card,.stat-card').forEach((el,i)=>{if(i<20)el.animate([{opacity:0,transform:'translateY(4px)'},{opacity:1,transform:'none'}],{duration:190,delay:Math.min(i*14,140),fill:'both'});});
})();
