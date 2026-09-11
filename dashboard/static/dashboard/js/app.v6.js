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

  function addSdgRow(host,prefix=''){
    const tpl=qs('#sdgTemplate'); if(!host||!tpl)return null;
    const n=host.querySelectorAll('[data-sdg-row]').length+1;
    const html=tpl.innerHTML.replaceAll('__N__',n).replaceAll('__PREFIX__',prefix);
    host.insertAdjacentHTML('beforeend',html);
    return host.lastElementChild;
  }

  document.addEventListener('click',e=>{
    const lineRemove=e.target.closest('[data-remove-line]');
    if(lineRemove){const host=lineRemove.closest('.line-repeater');const line=lineRemove.closest('.line-input');if(host&&line&&host.querySelectorAll('.line-input').length>1)line.remove();else if(line){const input=qs('input',line);if(input)input.value='';}return;}

    const addLine=e.target.closest('[data-add-line]');
    if(addLine){
      const host=qs(addLine.dataset.addLine);
      if(host){const name=addLine.dataset.lineName||'item[]',placeholder=addLine.dataset.placeholder||'Input value';host.insertAdjacentHTML('beforeend',`<div class="line-input"><input name="${name}" placeholder="${placeholder}"><button type="button" class="line-remove" data-remove-line aria-label="Remove">×</button></div>`);const input=host.lastElementChild&&qs('input',host.lastElementChild);if(input)input.focus();}
      return;
    }

    const addSdg=e.target.closest('[data-add-sdg]');
    if(addSdg){const host=qs(addSdg.dataset.addSdg);const row=addSdgRow(host,addSdg.dataset.sdgPrefix||'');if(row)qs('input',row)?.focus();return;}
    const removeSdg=e.target.closest('[data-remove-sdg]');
    if(removeSdg){const host=removeSdg.closest('.sdg-stack'),row=removeSdg.closest('[data-sdg-row]');if(host&&row&&host.querySelectorAll('[data-sdg-row]').length>1)row.remove();else if(row)qsa('input,textarea',row).forEach(x=>x.value='');return;}

    const rem=e.target.closest('[data-remove]');
    if(rem){const card=rem.closest('.activity-card,.project-card');if(card){card.animate([{opacity:1,transform:'scale(1)'},{opacity:0,transform:'scale(.985)'}],{duration:130}).onfinish=()=>card.remove();}return;}

    const add=e.target.closest('[data-add-activity]');
    if(add){const host=qs(add.dataset.addActivity),tpl=qs('#activityTemplate');if(host&&tpl){const n=host.querySelectorAll('.activity-card').length+1;host.insertAdjacentHTML('beforeend',tpl.innerHTML.replaceAll('__N__',n));const el=host.lastElementChild;el&&el.animate([{opacity:0,transform:'translateY(8px)'},{opacity:1,transform:'none'}],{duration:180});}return;}

    const nested=e.target.closest('[data-add-nested-activity]');
    if(nested){const host=nested.closest('.nested-activities'),prefix=host.dataset.prefix,n=host.querySelectorAll('.activity-card').length+1;const html=`<div class="activity-card compact"><div class="activity-head"><b>Activity ${n}</b><button type="button" class="icon danger-text" data-remove>Remove</button></div><div class="formgrid three"><label>Title<input name="${prefix}activity_title[]"></label><label>Date<input type="date" name="${prefix}activity_date[]"></label><label>Time<input type="time" name="${prefix}activity_time[]"></label><label>Venue<input name="${prefix}activity_venue[]"></label><label>Activity Leader<input name="${prefix}activity_leader[]"></label><label>Budget<input type="number" min="0" step="0.01" name="${prefix}activity_budget[]"></label></div><div class="formgrid three"><label>Topics<textarea name="${prefix}activity_topics[]" rows="2"></textarea></label><label>Objectives<textarea name="${prefix}activity_objectives[]" rows="2"></textarea></label><label>Learning Outcomes<textarea name="${prefix}activity_outcomes[]" rows="2"></textarea></label></div></div>`;nested.insertAdjacentHTML('beforebegin',html);return;}
  });

  const addProject=qs('#addProject'),projects=qs('#projects'),pt=qs('#projectTemplate');let pIndex=0;
  function addProjectCard(){
    if(!projects||!pt)return null;
    pIndex++;projects.insertAdjacentHTML('beforeend',pt.innerHTML.replaceAll('__IDX__',pIndex));
    const el=projects.lastElementChild;if(el){initToggles(el);el.animate([{opacity:0,transform:'translateY(10px)'},{opacity:1,transform:'none'}],{duration:180});}return el;
  }
  if(addProject&&projects&&pt){addProject.addEventListener('click',addProjectCard);}

  function syncReschedule(select){
    const target=qs(select.dataset.rescheduleTarget);if(!target)return;
    const show=select.value==='RESCHEDULED';target.classList.toggle('hidden',!show);
    const input=qs('input[type="date"]',target);if(input){input.required=show&&!select.disabled;if(!show)input.value='';}
  }
  qsa('.result-select').forEach(sel=>{sel.addEventListener('change',()=>syncReschedule(sel));syncReschedule(sel);});

  // Draft PPA editor hydration. This keeps draft data editable without changing saved/approved records.
  const initialEl=qs('#ppaInitialData');
  let initial={};
  if(initialEl){try{initial=JSON.parse(initialEl.textContent||'{}')||{};}catch(e){initial={};}}
  const hasInitial=!!(initial&&initial.id);

  function setField(root,name,value){
    const el=qs(`[name="${name}"]`,root||document);if(!el)return;
    if(el.type==='checkbox')el.checked=!!value;else el.value=value??'';
    if(el.matches('[data-toggle]')){el.dispatchEvent(new Event('change'));}
  }
  function setRepeater(host,name,values){
    if(!host)return;values=(values&&values.length)?values:[''];host.innerHTML='';
    values.forEach(v=>host.insertAdjacentHTML('beforeend',`<div class="line-input"><input name="${name}" value="${String(v??'').replaceAll('&','&amp;').replaceAll('"','&quot;')}" placeholder="Input value"><button type="button" class="line-remove" data-remove-line aria-label="Remove">×</button></div>`));
  }
  function ensureSdgRows(host,prefix,items){
    if(!host)return;items=(items&&items.length)?items:[{}];
    host.innerHTML='';items.forEach(()=>addSdgRow(host,prefix));
    const rows=qsa('[data-sdg-row]',host);
    items.forEach((item,i)=>{const row=rows[i];if(!row)return;setField(row,`${prefix}sdg_goal[]`,item.goal||'');setField(row,`${prefix}sdg_target[]`,item.target||'');setField(row,`${prefix}sdg_description[]`,item.description||'');setField(row,`${prefix}sdg_indicator[]`,item.indicator||'');});
  }
  function fillArray(root,name,items,key){qsa(`[name="${name}"]`,root).forEach((el,i)=>el.value=(items[i]&&items[i][key])||'');}
  function ensureActivities(host,addButton,items,prefix=''){
    const needed=Math.max(3,(items||[]).length);
    while(host&&host.querySelectorAll('.activity-card').length<needed){if(addButton)addButton.click();else break;}
    if(prefix){
      const fields={activity_title:'title',activity_date:'date',activity_time:'time',activity_venue:'venue',activity_leader:'leader',activity_topics:'topics',activity_objectives:'objectives',activity_outcomes:'outcomes',activity_budget:'budget'};
      Object.entries(fields).forEach(([n,k])=>fillArray(host,`${prefix}${n}[]`,items||[],k));
    }else{
      const fields={activity_title:'title',activity_date:'date',activity_time:'time',activity_venue:'venue',activity_leader:'leader',activity_topics:'topics',activity_objectives:'objectives',activity_outcomes:'outcomes',activity_budget:'budget'};
      Object.entries(fields).forEach(([n,k])=>fillArray(host,`${n}[]`,items||[],k));
    }
  }
  function fillPpa(root,prefix,data){
    ['notice_to_proceed_no','special_order_no','title','partner_category','partner_name','with_moa_mou','board_confirmed','board_resolution_no','board_resolution_date','leader_name','leader_position','leader_contact','assistant_name','assistant_position','assistant_contact','clientele','target_area','start_date','end_date','project_cost','funding_source','urdea'].forEach(n=>setField(root,`${prefix}${n}`,data[n]));
    const proHost=prefix?qs(`#project${prefix.match(/project_(\d+)_/)?.[1]}Proponents`,root):qs('#proponentLines');
    const memHost=prefix?qs(`#project${prefix.match(/project_(\d+)_/)?.[1]}Members`,root):qs('#memberLines');
    setRepeater(proHost,`${prefix}proponents[]`,data.proponents||[]);setRepeater(memHost,`${prefix}members[]`,data.members||[]);
    const sdgHost=prefix?qs(`#project${prefix.match(/project_(\d+)_/)?.[1]}Sdgs`,root):qs('#sdgRows');
    ensureSdgRows(sdgHost,prefix,data.sdgs||[]);
  }

  if(projects&&pt){
    if(hasInitial&&initial.ppa_type==='PROGRAM'){
      projects.innerHTML='';
      (initial.projects||[]).forEach(pr=>{const card=addProjectCard();if(!card)return;const idx=qs('input[name="project_index[]"]',card)?.value;const prefix=`project_${idx}_`;fillPpa(card,prefix,pr);ensureActivities(qs('.nested-activities',card),qs('[data-add-nested-activity]',card),pr.activities||[],prefix);});
      if(!(initial.projects||[]).length)addProjectCard();
    }else if(!hasInitial){addProjectCard();}
  }
  if(hasInitial){
    if(initial.ppa_type==='PROJECT'){
      fillPpa(document,'',initial);
      if(upi){upi.value=initial.umbrella_program_title||'';if(uph)uph.value=initial.umbrella_program||'';}
      ensureActivities(qs('#activities'),qs('[data-add-activity]'),initial.activities||[],'');
    }else if(initial.ppa_type==='PROGRAM'){
      fillPpa(document,'',initial);
    }
    initToggles();
  }

  const ppaForm=qs('#ppaForm');
  if(ppaForm){ppaForm.addEventListener('submit',e=>{
    const action=e.submitter&&e.submitter.value;if(action!=='save')return;
    const projectCards=qsa('[data-project]');
    let bad='';
    if(projectCards.length){
      projectCards.forEach(card=>{const title=qs('input[name$="_title"]',card)?.value?.trim()||'Untitled project';const count=qsa('input[name$="activity_title[]"]',card).filter(x=>x.value.trim()).length;if(count<3&&!bad)bad=`${title} needs at least 3 Activities before final Save.`;});
    }else{
      const count=qsa('input[name="activity_title[]"]',ppaForm).filter(x=>x.value.trim()).length;if(qs('#activities')&&count<3)bad='A Project needs at least 3 Activities before final Save.';
    }
    if(bad){e.preventDefault();alert(bad);}
  });}

  // Quarterly Monitoring Report project/status behavior.
  const qmrMetaEl=qs('#qmrProjectMeta'), qmrProject=qs('#qmrProject');
  if(qmrMetaEl&&qmrProject){
    let meta={};try{meta=JSON.parse(qmrMetaEl.textContent||'{}');}catch(e){meta={};}
    const status=qs('#id_project_status'), start=qs('#id_period_start'), end=qs('#id_period_end'), location=qs('#id_location'), funding=qs('#id_funding_source'), cost=qs('#id_total_project_cost'), school=qs('#id_school_name'), campus=qs('#id_campus_name');
    const ongoing=qs('#ongoingFields'), inactive=qs('#inactiveFields'), terminated=qs('#terminatedFields'), locked=qs('#terminationLocked'), termField=qs('#terminationDateField'), termInput=qs('#id_date_of_termination'), note=qs('#projectRuleNote');
    const selectedMeta=()=>meta[String(qmrProject.value)]||{};
    const syncStatus=()=>{
      const value=status?status.value:'';
      if(ongoing)ongoing.classList.toggle('hidden',value!=='ONGOING');
      if(inactive)inactive.classList.toggle('hidden',value!=='INACTIVE');
      if(terminated)terminated.classList.toggle('hidden',value!=='TERMINATED');
      if(value==='TERMINATED'){
        const m=selectedMeta(),eligible=!!m.termination_eligible;
        if(locked)locked.classList.toggle('hidden',eligible);if(termField)termField.classList.toggle('hidden',!eligible);if(termInput){termInput.disabled=!eligible;termInput.required=eligible;}
      } else if(termInput){termInput.required=false;}
    };
    const syncProject=()=>{
      const m=selectedMeta();
      if(start)start.value=m.start||'';if(end)end.value=m.end||'';if(school)school.value=m.school||'';if(campus)campus.value=m.campus||'';
      if(location&&m.location)location.value=m.location;if(funding&&m.funding)funding.value=m.funding;if(cost&&m.cost)cost.value=m.cost;
      const termOption=status&&qs('option[value="TERMINATED"]',status);if(termOption)termOption.disabled=!m.termination_eligible;
      if(note){if(m.auto_inactive){note.innerHTML=`<b>System status rule:</b> This Project currently meets the automatic Inactive rule (${m.not_conducted||0} monitored Activities are Not Conducted after the Project End Date).`;note.classList.remove('hidden');if(status&&!status.value)status.value='INACTIVE';}else if(m.completed){note.innerHTML='<b>Project activity monitoring:</b> Approved Activities are currently recorded as completed.';note.classList.remove('hidden');}else note.classList.add('hidden');}
      syncStatus();
    };
    qmrProject.addEventListener('change',syncProject);if(status)status.addEventListener('change',syncStatus);syncProject();syncStatus();
  }

  qsa('.card,.reference-card,.stat-card').forEach((el,i)=>{if(i<20)el.animate([{opacity:0,transform:'translateY(4px)'},{opacity:1,transform:'none'}],{duration:190,delay:Math.min(i*14,140),fill:'both'});});
})();
