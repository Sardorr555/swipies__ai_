(() => {
  if (document.getElementById('swipiesAcquisitionLink')) return;
  const desktop = document.querySelector('.sidebar-nav'), mobile = document.querySelector('.mobile-nav');
  if (!desktop) return;
  const link = document.createElement('a'); link.id='swipiesAcquisitionLink'; link.href='/admin/acquisition';
  link.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/></svg><span>Лендинги и UTM</span>';
  const media=matchMedia('(max-width:768px)');
  function place(){link.className=media.matches&&mobile?'mobile-nav-item':'nav-item';(media.matches&&mobile?mobile:desktop).append(link);}
  place();media.addEventListener('change',place);
  link.onclick=async event=>{
    event.preventDefault();const token=localStorage.getItem('swipies_admin_token');
    if(!token){location.assign('/admin.html');return;}
    try{const response=await fetch('/api/admin/acquisition/open',{method:'POST',headers:{Authorization:'Bearer '+token},cache:'no-store'});if(!response.ok)throw Error();location.assign('/admin/acquisition');}
    catch{if(typeof window.showToast==='function')window.showToast('Лендинги и UTM','Не удалось открыть страницу. Проверьте вход.','error');}
  };
})();
