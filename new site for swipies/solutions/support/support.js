(() => {
  'use strict';
  const lang=document.documentElement.lang;
  const content=window.SWIPIES_SUPPORT_I18N[lang] || window.SWIPIES_SUPPORT_I18N.ru;
  document.querySelectorAll('[data-language]').forEach(link=>{const url=new URL(link.href);url.search=location.search;url.hash=location.hash;link.href=url.toString();});
  const menu=document.querySelector('.menu-toggle'),nav=document.getElementById('navigation');
  function closeMenu(){menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label',content.menuOpen);nav.classList.remove('open');}
  menu.addEventListener('click',()=>{const expanded=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(expanded));menu.setAttribute('aria-label',expanded?content.menuClose:content.menuOpen);nav.classList.toggle('open',expanded);});
  nav.addEventListener('click',event=>{if(event.target.closest('a'))closeMenu();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){const open=menu.getAttribute('aria-expanded')==='true';closeMenu();if(open)menu.focus();}});
  const tabs=[...document.querySelectorAll('[data-scenario]')];
  function select(index,focus=false){
    const item=content.scenarios[index];
    tabs.forEach((tab,i)=>{tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1;});
    document.getElementById('support-conversation').setAttribute('aria-labelledby',tabs[index].id);
    document.getElementById('supportQuestion').textContent=item.question;
    const paragraph=document.createElement('p');paragraph.textContent=item.answer;
    document.getElementById('supportAnswer').replaceChildren(paragraph);
    document.getElementById('sourceName').textContent=item.source;
    document.getElementById('sourceDetail').textContent=item.detail;
    document.getElementById('supportOutcome').textContent=item.outcome;
    if(focus)tabs[index].focus();
  }
  tabs.forEach((tab,index)=>{
    tab.addEventListener('click',()=>select(index));
    tab.addEventListener('keydown',event=>{
      let next;
      if(event.key==='ArrowRight'||event.key==='ArrowDown')next=(index+1)%tabs.length;
      if(event.key==='ArrowLeft'||event.key==='ArrowUp')next=(index+tabs.length-1)%tabs.length;
      if(event.key==='Home')next=0;if(event.key==='End')next=tabs.length-1;
      if(next!==undefined){event.preventDefault();select(next,true);}
    });
  });
  select(0);
})();
