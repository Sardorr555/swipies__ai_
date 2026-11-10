(() => {
  'use strict';
  const lang = document.documentElement.lang;
  const labels = {ru:['Открыть меню','Закрыть меню'],uz:['Menyuni ochish','Menyuni yopish'],en:['Open menu','Close menu']}[lang] || ['Open menu','Close menu'];
  document.querySelectorAll('[data-language]').forEach(link=>{const url=new URL(link.href);url.search=location.search;url.hash=location.hash;link.href=url.toString();});
  const menu = document.querySelector('.menu-toggle');
  const nav = document.getElementById('navigation');
  menu.addEventListener('click', () => {
    const expanded=menu.getAttribute('aria-expanded')!=='true';
    menu.setAttribute('aria-expanded',String(expanded));
    menu.setAttribute('aria-label',expanded?labels[1]:labels[0]);
    nav.classList.toggle('open',expanded);
  });
  function closeMenu(){menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label',labels[0]);nav.classList.remove('open');}
  nav.addEventListener('click',event=>{if(event.target.closest('a'))closeMenu();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){const wasOpen=menu.getAttribute('aria-expanded')==='true';closeMenu();if(wasOpen)menu.focus();}});
  const scenarios=window.SWIPIES_SALES_DEMOS[document.documentElement.lang] || window.SWIPIES_SALES_DEMOS.ru;
  let active='products';
  const tabs=[...document.querySelectorAll('[data-scenario]')];
  const question=document.getElementById('demoQuestion'),answer=document.getElementById('demoAnswer'),prompts=document.getElementById('demoPrompts');
  function show(index){
    const item=scenarios[active][index];question.textContent=item.question;
    const text=document.createElement('p');text.textContent=item.answer;
    const outcome=document.createElement('small');outcome.className='answer-outcome';outcome.textContent=item.next;
    answer.replaceChildren(text,outcome);
    [...prompts.children].forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
  }
  function select(tab,focus=false){
    active=tab.dataset.scenario;
    tabs.forEach(item=>{const selected=item===tab;item.setAttribute('aria-selected',String(selected));item.tabIndex=selected?0:-1;});
    document.getElementById('demo-panel').setAttribute('aria-labelledby',tab.id);
    prompts.replaceChildren();
    scenarios[active].forEach((item,index)=>{const button=document.createElement('button');button.type='button';button.textContent=item.label;button.addEventListener('click',()=>show(index));prompts.append(button);});
    show(0);if(focus)tab.focus();
  }
  tabs.forEach((tab,index)=>{
    tab.addEventListener('click',()=>select(tab));
    tab.addEventListener('keydown',event=>{
      let next;
      if(event.key==='ArrowRight'||event.key==='ArrowDown')next=(index+1)%tabs.length;
      if(event.key==='ArrowLeft'||event.key==='ArrowUp')next=(index+tabs.length-1)%tabs.length;
      if(event.key==='Home')next=0;if(event.key==='End')next=tabs.length-1;
      if(next!==undefined){event.preventDefault();select(tabs[next],true);}
    });
  });
  select(tabs[0]);
})();
