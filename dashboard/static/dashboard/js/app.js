(function(){
  document.querySelectorAll('[data-menu]').forEach(btn=>btn.addEventListener('click',e=>{e.stopPropagation();const id=btn.dataset.menu;document.querySelectorAll('.menu').forEach(m=>{if(m.id!==id)m.classList.remove('open')});document.getElementById(id)?.classList.toggle('open')}));
  document.addEventListener('click',()=>document.querySelectorAll('.menu').forEach(m=>m.classList.remove('open')));

  document.querySelectorAll('[data-modal]').forEach(btn=>btn.addEventListener('click',()=>document.getElementById(btn.dataset.modal)?.classList.add('open')));
  document.querySelectorAll('[data-close]').forEach(btn=>btn.addEventListener('click',()=>btn.closest('.modal')?.classList.remove('open')));

  document.querySelectorAll('[data-return]').forEach(btn=>btn.addEventListener('click',()=>{const modal=document.getElementById('returnmodal');const form=document.getElementById('returnform');if(form)form.action=btn.dataset.return;if(modal)modal.classList.add('open')}));

  const checks=[...document.querySelectorAll('#indicators input[name="indicator"]')];
  checks.forEach(c=>c.addEventListener('change',()=>{const on=checks.filter(x=>x.checked);if(on.length>4){c.checked=false;alert('Select up to four indicators only.')}}));

  function n(el){const v=parseFloat(el?.value||'0');return isNaN(v)?0:v}
  function fmt(v,percent){if(percent)return Number(v.toFixed(2));return Math.round(v)}

  document.querySelectorAll('.entrytable').forEach(table=>{
    const percent=table.dataset.percent==='1';
    const rows=[...table.querySelectorAll('tr')].slice(1,-1);
    const totalRow=table.querySelector('.totrow');
    function calc(){
      const colCount=rows[0]?.querySelectorAll('td').length||0;
      const colSums=new Array(colCount).fill(0);
      rows.forEach(row=>{
        const cells=[...row.querySelectorAll('td')];
        let rowTotal=0;
        cells.forEach((cell,i)=>{const input=cell.querySelector('input');if(input){const value=n(input);colSums[i]+=value;if(i>0)rowTotal+=value;}});
        const rt=row.querySelector('.rt');if(rt)rt.textContent=fmt(rowTotal,percent)+(percent?'%':'');
      });
      if(totalRow){const cells=[...totalRow.querySelectorAll('td')];cells.forEach((cell,i)=>{if(i<colSums.length)cell.textContent=fmt(colSums[i],percent)+(percent?'%':'')});const gt=totalRow.querySelector('.gt');if(gt){const g=colSums.slice(1).reduce((a,b)=>a+b,0);gt.textContent=fmt(g,percent)+(percent?'%':'')}}
    }
    table.querySelectorAll('input').forEach(i=>i.addEventListener('input',calc));calc();
  });

  document.querySelectorAll('.officialtable tr[data-percent]').forEach(row=>{
    const percent=row.dataset.percent==='1';const t=[...row.querySelectorAll('.tq')],a=[...row.querySelectorAll('.aq')];
    function calc(){const tv=t.reduce((s,e)=>s+n(e),0),av=a.reduce((s,e)=>s+n(e),0);row.querySelector('.tt').textContent=fmt(tv,percent)+(percent?'%':'');row.querySelector('.at').textContent=fmt(av,percent)+(percent?'%':'');row.querySelector('.var').textContent=fmt(av-tv,percent)+(percent?'%':'')}
    [...t,...a].forEach(i=>i.addEventListener('input',calc));calc();
  });

  function renumberQpar(){document.querySelectorAll('#qtable tr').forEach((row,idx)=>{if(idx===0)return;const nidx=idx-1;const ind=row.querySelector('[name="indicator"]');if(ind)ind.name='indicator';row.querySelectorAll('input,textarea').forEach(el=>{if(el.name.startsWith('target_'))el.name=`target_${nidx}`;if(el.name.startsWith('value_')){const code=el.name.split('_').pop();el.name=`value_${nidx}_${code}`;}if(el.name.startsWith('mov_'))el.name=`mov_${nidx}`;if(el.name.startsWith('remarks_'))el.name=`remarks_${nidx}`;});});}
  const add=document.getElementById('addrow');if(add){add.addEventListener('click',()=>{const table=document.getElementById('qtable');const last=table.querySelector('tr:last-child');const row=last.cloneNode(true);row.querySelectorAll('input,textarea').forEach(i=>{i.value=''});row.querySelector('.rt').textContent='0';table.appendChild(row);renumberQpar();wireQpar();});}
  function wireQpar(){document.querySelectorAll('#qtable .remove').forEach(b=>b.onclick=()=>{if(document.querySelectorAll('#qtable tr').length>2){b.closest('tr').remove();renumberQpar();}});document.querySelectorAll('#qtable tr').forEach((row,idx)=>{if(idx===0)return;const inputs=[...row.querySelectorAll('.qval')],rt=row.querySelector('.rt');const calc=()=>{rt.textContent=Math.round(inputs.reduce((s,e)=>s+n(e),0))};inputs.forEach(i=>i.oninput=calc);calc();});}
  wireQpar();
  const quarter=document.getElementById('quarter'),months=document.getElementById('months');function qm(){if(!quarter||!months)return;months.textContent={1:'JAN–MARCH',2:'APR–JUNE',3:'JUL–SEPT',4:'OCT–DEC'}[quarter.value]||''}if(quarter){quarter.addEventListener('change',qm);qm();}

  // PPA approval logic: Date Approved only applies to approved records.
  const approvedBox=document.getElementById('id_approved');
  const approvalDate=document.getElementById('id_date_approved');
  function syncApprovalDate(){
    if(!approvedBox||!approvalDate)return;
    approvalDate.disabled=!approvedBox.checked;
    if(!approvedBox.checked)approvalDate.value='';
    const wrap=document.getElementById('approval-date-wrap');
    if(wrap)wrap.classList.toggle('field-disabled',!approvedBox.checked);
  }
  if(approvedBox){approvedBox.addEventListener('change',syncApprovalDate);syncApprovalDate();}
})();
