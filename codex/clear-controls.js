let clearBusy=false, clearAvailable=false;
async function loadClearCapabilities(){
  const button=$('#clear-codes-btn'),note=$('#clear-codes-note');
  if(previewMode){note.textContent='Code clearing requires a live connection. Preview mode never writes to the car.';return;}
  try{
    const capabilities=await api('/api/capabilities');
    clearAvailable=capabilities.clear_emissions_codes===true;
    button.disabled=!clearAvailable;
    note.textContent=clearAvailable?'Clear engine emissions codes with the ignition on and engine off. You will be asked to confirm.':'Code clearing is not available on this backend.';
    if(clearAvailable)document.querySelector('.colophon p').textContent='Live diagnostics. Clearing engine codes requires explicit confirmation.';
  }catch{note.textContent='Code clearing needs the updated backend. Live diagnostics remain available.';}
}
$('#clear-codes-btn').onclick=()=>{if(clearAvailable&&!clearBusy)$('#clear-dialog').showModal();};
$('#clear-cancel').onclick=()=>$('#clear-dialog').close();
$('#clear-dialog').addEventListener('cancel',event=>{if(clearBusy)event.preventDefault();});
$('#clear-confirm').onclick=async()=>{
  if(clearBusy||!clearAvailable)return;
  clearBusy=true;
  for(const id of ['clear-confirm','clear-cancel','clear-codes-btn','codes-btn'])$('#'+id).disabled=true;
  $('#clear-confirm').textContent='Clearing…';
  const resultBox=$('#clear-result');
  resultBox.hidden=false;resultBox.textContent='Checking engine state and saving the current emissions codes…';
  try{
    const response=await fetch('/api/dtcs/clear',{method:'POST',headers:{'Content-Type':'application/json','X-Pdiag-Action':'clear-emissions-codes'},body:JSON.stringify({confirmed:true,request_id:crypto.randomUUID()})});
    const result=await response.json();
    if(!response.ok)throw new Error(result.error||'The clearing request could not be completed. Read the codes again.');
    resultBox.textContent=result.message+(result.monitor_status?' '+result.monitor_status+'.':'')+(result.audit_saved?'':' The result could not be added to the local log.');
    resultBox.dataset.state=result.cleared?'ok':'attention';
    // This is a separate DME read, which may include manufacturer-specific faults
    // outside the scope of standard OBD emissions clearing.
    await loadCodes();
  }catch(error){resultBox.textContent=error.message;resultBox.dataset.state='attention';}
  finally{
    clearBusy=false;$('#clear-dialog').close();
    for(const id of ['clear-confirm','clear-cancel','clear-codes-btn','codes-btn'])$('#'+id).disabled=false;
    $('#clear-confirm').textContent='Clear engine codes';
    resultBox.scrollIntoView({block:'nearest',behavior:reduceMotion?'instant':'smooth'});
  }
};
