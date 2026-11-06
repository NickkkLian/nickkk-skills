const $ = selector => document.querySelector(selector);
const skills = window.SAMPLE;
const groups = {
  numbers:['nk-data-story','nk-model','nk-design','nk-explorer','nk-clean-list'],
  checks:['nk-two-brain','nk-evidence-audit','nk-regression-baseline','nk-rewrite-coverage'],
  guards:['nk-git-guardrail-hook','nk-indent-guard'],
  writing:['nk-deck','nk-post-kit','nk-x-post-desk']
};
const labels={numbers:'Numbers',checks:'Checks',guards:'Repository',writing:'Writing'};
let group='all';
const normalize=value=>value.toLowerCase().replace(/[-_’']/g,' ').replace(/\b(?:csv|excel|xlsx|workbooks?)\b/g,'spreadsheet').replace(/\bcontacts\b/g,'contact').replace(/\s+/g,' ').trim();
function installCommand(skill){return $('#assistant').value==='claude'?`/plugin install ${skill.name}@nickkk-skills`:`codex plugin add ${skill.name}@nickkk-skills`;}
function render(){
  const route=$('#assistant').value;
  const terms=normalize($('#search').value).split(' ').filter(Boolean);
  $('#marketplace-command').textContent=route==='claude'?'/plugin marketplace add NickkkLian/nickkk-skills':'codex plugin marketplace add NickkkLian/nickkk-skills';
  $('#install-note').textContent=route==='claude'?'Run in Claude Code, then start a new session.':'Run in your terminal, then start a new Codex session.';
  const visible=skills.filter(skill=>(group==='all'||groups[group].includes(skill.name))&&terms.every(term=>normalize(`${skill.name} ${skill.description} ${skill.keywords}`).includes(term)));
  $('#result-count').textContent=`${visible.length} ${visible.length===1?'skill':'skills'}`;
  $('#no-results').hidden=visible.length!==0;
  $('#catalogue').replaceChildren();
  $('#catalogue').classList.toggle('single-result',visible.length===1);
  for(const skill of visible){
    const category=Object.keys(groups).find(name=>groups[name].includes(skill.name));
    const supported=route==='claude'||skill.name!=='nk-git-guardrail-hook';
    const article=document.createElement('article');
    article.className='skill';article.id=skill.name;
    article.innerHTML=`<div class="skill-heading"><div class="skill-icon">${window.SKILL_ICONS[skill.name]}</div><div><h2><a href="${skill.source}">${skill.name}</a></h2><span class="skill-category">${labels[category]}</span></div></div><p class="skill-purpose"></p>${supported?'<div class="skill-command"><code></code><button class="icon-button" aria-label="Copy install command"></button></div>':'<p class="compatibility-warning">This hook requires Claude Code. Choose Claude Code for its install command.</p>'}<p class="command-status"></p><details><summary>Output and compatibility</summary><p class="skill-note"></p></details><div class="skill-links"><a href="${skill.source}">Documentation</a><a href="${skill.source}#compatibility">Test notes</a></div>`;
    article.querySelector('.skill-purpose').textContent=skill.description;
    article.querySelector('.skill-note').textContent=route==='codex'?skill.codex:'Read the recorded checks and limits before using this skill.';
    const status=article.querySelector('.command-status');
    status.append(document.createTextNode(route==='codex'?skill.codex:'Claude Code: recorded checks. '));
    const notes=document.createElement('a'); notes.href=`${skill.source}#compatibility`; notes.textContent='Test notes'; status.append(' ',notes);
    if(supported){
      article.querySelector('code').textContent=installCommand(skill);
      const button=article.querySelector('.skill-command button');
      button.innerHTML=ui.icons.copy;
      if(skill.name==='nk-data-story'){button.dataset.mainAction='';button.dataset.actionName='Copy nk-data-story install command';}
      button.addEventListener('click',()=>copy(installCommand(skill),button));
    }
    const details = article.querySelector('details');
    const clone = document.createElement('div');
    clone.className = 'clone-command';
    const cloneCode = document.createElement('code');
    const destination = route === 'claude' ? '~/.claude/skills/' : '~/.agents/skills/';
    cloneCode.textContent = `git clone ${skill.source}${route === 'codex' ? '.git' : ''} ${destination}${skill.name}`;
    if (supported) {
      const cloneCopy = document.createElement('button');
      cloneCopy.type = 'button';
      cloneCopy.textContent = 'Copy clone command';
      cloneCopy.addEventListener('click', () => copy(cloneCode.textContent, cloneCopy));
      clone.append(cloneCode, cloneCopy);
      details.append(clone);
    }
    const preview = document.createElement('img');
    preview.className = 'skill-demo';
    preview.loading = 'lazy';
    preview.src = `assets/demos/${skill.name}.png`;
    preview.alt = `${skill.name} recorded demonstration using synthetic data`;
    const actions = document.createElement('div');
    actions.className = 'demo-actions';
    const play = document.createElement('button');
    play.type = 'button';
    play.textContent = 'Play demo';
    let playing = false;
    play.addEventListener('click', () => {
      if (ui.reduced()) {
        $('#announcement').textContent = 'Reduced motion is enabled. Open the recording link to view it.';
        $('#announcement').hidden = false;
        return;
      }
      playing = !playing;
      preview.src = `assets/demos/${skill.name}.${playing ? 'gif' : 'png'}`;
      play.textContent = playing ? 'Stop demo' : 'Play demo';
    });
    const original = document.createElement('a');
    original.href = `assets/demos/${skill.name}.gif`;
    original.textContent = 'Open recording';
    actions.append(play, original);
    details.append(preview, actions);
    $('#catalogue').append(article);
  }
  ui.fade($('#catalogue'));
  document.querySelectorAll('[data-assistant]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.assistant===route)));
  document.querySelectorAll('[data-group]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.group===group)));
  const featuring=group==='all'&&!$('#search').value.trim();
  $('.featured').hidden=!featuring;
  $('#featured-code').textContent=installCommand(skills[0]);
  $('#featured-copy').toggleAttribute('data-main-action',featuring);
  $('#featured-copy').dataset.actionName='Copy nk-data-story install command';
  if(featuring)$('#catalogue [data-main-action]')?.removeAttribute('data-main-action');
}
let announcementTimer;
async function copy(command,button){
  try{
    await navigator.clipboard.writeText(command);
    button.innerHTML=ui.icons.check;
    button.setAttribute('aria-label','Copied');
    ui.animate(button,[{transform:'scale(.9)',opacity:.5},{transform:'scale(1)',opacity:1}],180);
    $('#announcement').textContent='Command copied';
  }catch{
    const code=button.parentElement.querySelector('code');
    const range=document.createRange();range.selectNodeContents(code);
    const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
    $('#announcement').textContent='Command selected. Copy the selected text.';
  }
  $('#announcement').hidden=false;
  clearTimeout(announcementTimer);
  announcementTimer=setTimeout(()=>{$('#announcement').hidden=true;},3000);
}
$('#copy-marketplace').innerHTML=ui.icons.copy;
$('#copy-marketplace').addEventListener('click',()=>copy($('#marketplace-command').textContent,$('#copy-marketplace')));
$('#assistant').addEventListener('change',render);
$('#search').addEventListener('input',render);
document.querySelectorAll('[data-assistant]').forEach(button=>button.addEventListener('click',()=>{
  $('#assistant').value=button.dataset.assistant;
  $('#assistant').dispatchEvent(new Event('change'));
}));
document.querySelectorAll('[data-group]').forEach(button=>button.addEventListener('click',()=>{group=button.dataset.group;render();}));
document.addEventListener('keydown',event=>{if((event.metaKey||event.ctrlKey)&&event.key==='k'){event.preventDefault();$('#search').focus();}});
const featured=window.FEATURED_EVIDENCE, percent=(featured.result.value*100).toFixed(1);
$('#featured-cards').innerHTML=`<article class="featured-card"><div><h3>nk-data-story</h3><p>Monday share of paid sales</p><p>${featured.result.n.toLocaleString()} rows · ${featured.result.skipped} skipped<br>${featured.window.from}–${featured.window.to}<br>Recorded synthetic example</p></div><figure class="specimen"><strong>${percent}%</strong><div class="specimen-share" role="img" aria-label="Monday ${percent} percent of paid sales"><span style="width:${percent}%"></span></div><small>of paid sales on Mondays</small></figure><div class="featured-install"><p>Install the skill behind this result</p><div class="skill-command"><code id="featured-code"></code><button id="featured-copy" class="icon-button" aria-label="Copy nk-data-story install command"></button></div></div><details class="featured-evidence"><summary>See the report and run evidence</summary><p>Fictional bakery input: <a href="assets/featured/bakery-2025.csv">synthetic CSV</a> and <a href="assets/featured/report.json">report specification</a>. The <a href="https://github.com/NickkkLian/nickkk-skills/blob/main/plugins/nk-data-story/skills/nk-data-story/scripts/render.py">render script</a> recomputed the figures and ran the report check: ${featured.check.toLowerCase()}${featured.warnings.length ? ` (${featured.warnings.length} ${featured.warnings.length===1?"warning":"warnings"})` : ''}. See the <a href="assets/featured/evidence.json">run record</a> and <a href="assets/featured/report.html">rendered report</a>.</p><a href="assets/featured/recorded-report.png"><img src="assets/featured/recorded-report.png" alt="Open the recorded synthetic bakery report image"></a></details></article>`;
$('#featured-copy').innerHTML=ui.icons.copy;
$('#featured-copy').addEventListener('click',()=>copy(installCommand(skills[0]),$('#featured-copy')));
render();
document.documentElement.dataset.ready='true';
