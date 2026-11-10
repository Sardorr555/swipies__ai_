(() => {
 'use strict';
 const data=window.SWIPIES_KNOWLEDGE_I18N?.[document.documentElement.lang];
 if(!data)return;
 document.querySelectorAll('[data-language]').forEach(link=>{const url=new URL(link.href);url.search=location.search;url.hash=location.hash;link.href=url.toString();});
 const menu=document.querySelector('.menu-toggle'),nav=document.getElementById('navigation');
 const close=()=>{menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label',data.menuOpen);nav.classList.remove('open');};
 menu.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));menu.setAttribute('aria-label',open?data.menuClose:data.menuOpen);nav.classList.toggle('open',open);});
 nav.addEventListener('click',event=>{if(event.target.closest('a'))close();});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'){const open=menu.getAttribute('aria-expanded')==='true';close();if(open)menu.focus();}});
 const tabs=[...document.querySelectorAll('[data-case]')],citations=document.getElementById('citations');
 let current=0;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 function source(index){
  const item=data.cases[current],citation=item.citations[index];
  document.getElementById('sourceFile').querySelector('span').textContent=item.file;
  document.getElementById('sourcePage').textContent=citation.page;
  document.getElementById('sourceQuote').textContent=citation.quote;
  document.getElementById('sourceSection').textContent=citation.label;
  document.getElementById('sourceCounter').textContent=String(index+1).padStart(2,'0')+' / '+String(item.citations.length).padStart(2,'0');
  [...citations.children].forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
  if(!reduced.matches)document.getElementById('sourceQuote').animate([{opacity:.3,transform:'translateY(4px)'},{opacity:1,transform:'translateY(0)'}],{duration:180,easing:'ease-out'});
 }
 function select(index,focus=false){
  current=index;const item=data.cases[index];
  tabs.forEach((tab,i)=>{tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1;});
  document.getElementById('answer-panel').setAttribute('aria-labelledby',tabs[index].id);
  document.getElementById('questionText').textContent=item.question;
  document.getElementById('answerText').textContent=item.answer;
  const template=citations.querySelector('button')?.cloneNode(true);
  citations.replaceChildren();
  item.citations.forEach((citation,i)=>{
   const button=template.cloneNode(true);button.dataset.citation=String(i);button.setAttribute('aria-pressed',String(i===0));
   button.querySelector('span').textContent='['+String(i+1)+']';
   // Replace just the translated label between the reference number and SVG.
   [...button.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE).forEach(node=>node.remove());
   button.insertBefore(document.createTextNode(citation.label),button.querySelector('svg'));
   button.addEventListener('click',()=>source(i));citations.append(button);
  });
  source(0);if(focus)tabs[index].focus();
 }
 tabs.forEach((tab,index)=>{
  tab.addEventListener('click',()=>select(index));
  tab.addEventListener('keydown',event=>{let next;if(['ArrowRight','ArrowDown'].includes(event.key))next=(index+1)%tabs.length;if(['ArrowLeft','ArrowUp'].includes(event.key))next=(index+tabs.length-1)%tabs.length;if(event.key==='Home')next=0;if(event.key==='End')next=tabs.length-1;if(next!==undefined){event.preventDefault();select(next,true);}});
 });
 select(0);
 if('IntersectionObserver' in window&&!reduced.matches){
  document.documentElement.classList.add('enhanced');
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('visible');observer.unobserve(entry.target);}}),{threshold:.06});
  document.querySelectorAll('.reveal').forEach(element=>observer.observe(element));
 }
})();
