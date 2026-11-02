function nextCycleLabel(){
  const parts=new Intl.DateTimeFormat('en-US',{
    timeZone:'America/New_York',hour:'2-digit',minute:'2-digit',hour12:false,weekday:'short'
  }).formatToParts(new Date());
  const h=Number(parts.find(x=>x.type==='hour')?.value||0);
  const m=Number(parts.find(x=>x.type==='minute')?.value||0);
  const t=h*60+m;
  if(t<525)return '08:45 ET · PREMARKET';
  if(t<575)return '09:35 ET · PAPER EXECUTION';
  if(t<995)return '16:35 ET · POST-CLOSE';
  return '08:45 ET · NEXT SESSION';
}
