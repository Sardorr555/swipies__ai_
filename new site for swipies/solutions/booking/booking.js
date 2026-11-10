(() => {
 'use strict';
 const content=window.SWIPIES_BOOKING_I18N?.[document.documentElement.lang];
 if(!content)return;
 document.querySelectorAll('[data-language]').forEach(link=>{const url=new URL(link.href);url.search=location.search;url.hash=location.hash;link.href=url.toString();});
 const menu=document.querySelector('.menu-toggle'),nav=document.getElementById('navigation');
 function close(){menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label',content.menuOpen);nav.classList.remove('open');}
 menu.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));menu.setAttribute('aria-label',open?content.menuClose:content.menuOpen);nav.classList.toggle('open',open);});
 nav.addEventListener('click',event=>{if(event.target.closest('a'))close();});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'){const open=menu.getAttribute('aria-expanded')==='true';close();if(open)menu.focus();}});
 const services=[...document.querySelectorAll('[data-service]')],days=[...document.querySelectorAll('[data-day]')],slotOptions=document.getElementById('slotOptions');
 const result=document.getElementById('demoResult'),resultButton=document.getElementById('resultButton');
 let service=0,day=0,slot=null;
 function summary(){
  document.getElementById('summaryService').textContent=content.services[service].name;
  document.getElementById('summaryDay').textContent=content.weekdays[day]+' / '+String(9+day).padStart(2,'0');
  document.getElementById('summaryTime').textContent=slot||'—';
  resultButton.disabled=!slot;
  result.hidden=true;resultButton.hidden=false;
 }
 function renderSlots(){
  slot=null;slotOptions.replaceChildren();
  const times=window.SWIPIES_BOOKING_EXAMPLE_SLOTS[service][day];
  times.forEach(time=>{
   const button=document.createElement('button');button.type='button';button.textContent=time;button.dataset.slot=time;button.setAttribute('aria-pressed','false');
   button.addEventListener('click',()=>{slot=time;[...slotOptions.children].forEach(item=>item.setAttribute('aria-pressed',String(item===button)));document.getElementById('slotHint').textContent=content.timezone||'';summary();});
   slotOptions.append(button);
  });
  document.getElementById('slotHint').textContent=times.length?content.pickSlot:content.empty;
  document.getElementById('durationText').textContent=content.services[service].duration+' '+content.minutes;
  summary();
 }
 function chooseService(index,focus=false){
  service=index;services.forEach((button,i)=>{button.setAttribute('aria-checked',String(i===index));button.tabIndex=i===index?0:-1;});
  renderSlots();if(focus)services[index].focus();
 }
 services.forEach((button,index)=>{
  button.addEventListener('click',()=>chooseService(index));
  button.addEventListener('keydown',event=>{let next;if(['ArrowRight','ArrowDown'].includes(event.key))next=(index+1)%services.length;if(['ArrowLeft','ArrowUp'].includes(event.key))next=(index+services.length-1)%services.length;if(event.key==='Home')next=0;if(event.key==='End')next=services.length-1;if(next!==undefined){event.preventDefault();chooseService(next,true);}});
 });
 days.forEach((button,index)=>button.addEventListener('click',()=>{day=index;days.forEach((item,i)=>item.setAttribute('aria-pressed',String(i===index)));renderSlots();}));
 resultButton.addEventListener('click',()=>{if(!slot)return;result.hidden=false;resultButton.hidden=true;result.focus({preventScroll:true});});
 document.getElementById('resetButton').addEventListener('click',()=>{renderSlots();slotOptions.querySelector('button')?.focus();});
 renderSlots();
})();
