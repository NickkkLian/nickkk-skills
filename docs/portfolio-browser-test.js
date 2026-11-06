// Executed against the served catalogue by the workspace browser check.
async function portfolioBrowserTest() {
  const assert = (ok, message) => { if (!ok) throw Error(message); };
  const $ = s => document.querySelector(s);
  const search = value => { $('#search').value = value; $('#search').dispatchEvent(new Event('input', {bubbles:true})); };
  const record = window.FEATURED_EVIDENCE;
  assert(record.synthetic && $('.specimen strong').textContent === (record.result.value*100).toFixed(1)+'%', 'specimen from synthetic evidence');
  assert($('.featured-evidence a[href$="recorded-report.png"]') && $('.featured-evidence a[href$="report.html"]') && $('.featured-evidence a[href$="evidence.json"]'), 'report and evidence links');
  $('.featured-evidence').open = true;
  const image = $('.featured-evidence img'), frame = $('.featured-evidence > a');
  assert(Math.abs(image.getBoundingClientRect().width - frame.clientWidth) < 2 && getComputedStyle(frame).overflowY === 'auto', 'featured report uses full width with bounded scroll');
  search('clean csv');
  assert($('#nk-clean-list') && $('#catalogue').classList.contains('single-result'), 'clean csv finds one full-width result');
  search('contact export'); assert($('#nk-clean-list'), 'contact export synonym');
  search('excel'); assert($('#nk-data-story') && $('#nk-clean-list'), 'Excel and spreadsheet synonyms');
  $('[data-assistant="codex"]').click(); search('nk-two-brain');
  assert(/not tested/i.test($('#nk-two-brain .command-status').textContent) && $('#nk-two-brain .command-status a').href.endsWith('#compatibility'), 'untested status by Codex command');
  const card=$('#nk-two-brain'), evidence=card.querySelector('.skill-evidence'), clone=card.querySelector('.clone-command');
  evidence.open=true; clone.open=true;
  assert((card.textContent.match(/not tested in this assistant/gi)||[]).length === 1 && card.querySelectorAll('a[href$="#compatibility"]').length === 1, 'one compatibility status and notes link');
  assert(clone.closest('.skill-main') && /Or install by cloning/.test(clone.querySelector('summary').textContent) && !evidence.querySelector('code'), 'clone fallback stays beside the plugin command');
  const poster=card.querySelector('.skill-demo'); await poster.decode();
  assert(poster.src.endsWith('-poster.png') && poster.naturalWidth > 0, 'recording uses the extracted final-frame poster');
  assert(parseFloat(getComputedStyle(card.querySelector('.demo-actions button')).borderRadius) > 0 && parseFloat(getComputedStyle(clone.querySelector('button')).borderWidth) > 0, 'demo and clone buttons have borders and radius');
  if(innerWidth > 700) assert(evidence.getBoundingClientRect().left > card.querySelector('.skill-main').getBoundingClientRect().right, 'evidence sits beside the command at desktop widths');
  search('nk-explorer'); assert(/partial/i.test($('#nk-explorer .command-status').textContent), 'partial status by command');
  search('nk-git-guardrail-hook'); assert(/requires Claude Code/.test($('.compatibility-warning').textContent) && !$('#nk-git-guardrail-hook .skill-command'), 'unsupported route remains unavailable');
  search('no such task xyz'); assert(!$('#no-results').hidden, 'empty-state recovery');
  return 'Catalogue: featured width, search, single status, clone fallback, final-frame poster and desktop evidence layout passed';
}
