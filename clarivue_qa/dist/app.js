'use strict';
const $ = selector => document.querySelector(selector);
const questions = {running:'Why have I been developing chest pains while running?',angina:'What is the connection between angina and physical exertion?'};
let mode = 'everyday', liveResponse = null, requestVersion = 0, controller;
const escapeHTML = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const cite = id => `<button class="cite" data-source="${escapeHTML(id)}" aria-label="Inspect source ${escapeHTML(id)}">${escapeHTML(id)}</button>`;
function citedText(text) {
  const ids = new Set((liveResponse?.citations || []).map(c => c.evidence_id));
  return escapeHTML(text).replace(/\[Evidence\s+(\d+)\]/g, (match, n) => ids.has(`evidence_${n}`) ? cite(`evidence_${n}`) : match);
}
function render() {
  document.querySelectorAll('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
  $('#view-description').textContent = {everyday:'The answer and its supporting evidence.',learner:'Learn the concepts and the limits of the evidence.',clinical:'Query structure, graph associations, and source provenance.'}[mode];
  $('.sample-label').textContent = liveResponse ? 'Live backend response' : 'Ready for your question';
  $('#answer').innerHTML = liveResponse
    ? `<h2>${escapeHTML(liveResponse.headline)}</h2>${liveResponse.paragraphs.map(p => `<p style="white-space:pre-wrap">${citedText(p)}</p>`).join('')}<div class="safety"><p>${escapeHTML(liveResponse.safety)}</p></div>`
    : '<h2>Explore a question with your indexed research.</h2><p>Submit your question to retrieve evidence and generate a grounded answer.</p>';
  $('#uncertainty-body').textContent = liveResponse?.uncertainty || 'Answers depend on the coverage and quality of the indexed corpus.';
  $('#entities').innerHTML = liveResponse?.entities.length ? liveResponse.entities.map(e => `<div class="entity"><small>${escapeHTML(e.type)}${e.negated ? ' · NEGATED' : ''}</small>${escapeHTML(e.name)}</div>`).join('') : '<p>No extracted concepts to display.</p>';
  $('#missing').innerHTML = (liveResponse?.missing_context || []).map(x => `<span>${escapeHTML(x)}</span>`).join('');
  const paths = liveResponse?.graph_paths || [];
  $('#connections').innerHTML = paths.length ? paths.map(path => `<div class="connection">${(path.edges || []).map(edge => `<p>${escapeHTML(edge.source)} → ${escapeHTML(edge.relation)} → ${escapeHTML(edge.target)}${edge.evidence_source ? `<br><small>${escapeHTML(edge.evidence_source)}</small>` : ''}</p>`).join('')}</div>`).join('') + '<p class="fineprint">Graph associations guide retrieval; they are not supporting passages or diagnostic probabilities.</p>' : `<p>${liveResponse?.knowledge_graph?.enabled ? 'No graph paths matched this question.' : 'Knowledge graph enrichment is not configured.'}</p>`;
  if (liveResponse?.knowledge_graph?.metadata?.status === 'demo_unverified') $('#connections').innerHTML += '<p class="fineprint">This graph contains unverified demonstration associations.</p>';
  $('#learning-note').hidden = mode !== 'learner';
  $('#learning-note').textContent = 'Graph associations guide the evidence search. Supporting passages, rather than graph connections alone, ground the answer.';
  $('#extraction-title').textContent = mode === 'clinical' ? 'Extracted query structure' : 'What we understood';
  $('#connections-title').textContent = 'Graph associations';
  $('#instructions').hidden = mode !== 'clinical';
  const sources = liveResponse?.sources || [];
  $('#evidence .section-heading > span').textContent = `${sources.length} retrieved passages`;
  $('.source-grid').innerHTML = sources.length ? sources.map(source => {
    let url = null;
    try { const parsed = new URL(source.url); if (['http:', 'https:'].includes(parsed.protocol)) url = parsed.href; } catch {}
    return `<article class="source-card" id="source-${escapeHTML(source.id)}" tabindex="-1"><div class="source-top"><span class="source-number">${escapeHTML(source.id)}</span><span>${escapeHTML(source.kind)}</span></div><h3>${escapeHTML(source.title)}</h3><p class="source-summary">${escapeHTML(source.summary)}</p><details><summary>Read supporting passage</summary><blockquote>${escapeHTML(source.passage)}</blockquote><p>${escapeHTML(source.detail)}</p><p>Document: ${escapeHTML(source.document_id)} · Chunk: ${escapeHTML(source.chunk_id)}</p></details><div class="source-bottom"><span>${escapeHTML(source.date)}</span>${url ? `<a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>` : ''}</div></article>`;
  }).join('') : '<p>No retrieved passages to display.</p>';
}
function clearRequest() {
  requestVersion++;
  controller?.abort();
  liveResponse = null;
  $('#question-form button[type="submit"]').disabled = false;
  render();
}
function loadExample(name) {
  if (!Object.hasOwn(questions, name)) return;
  clearRequest();
  $('#question').value = questions[name];
  $('#notice').hidden = true;
  document.querySelectorAll('[data-example]').forEach(b => b.classList.toggle('active', b.dataset.example === name));
}
async function submitQuestion(event) {
  event.preventDefault();
  const question = $('#question').value.trim();
  clearRequest();
  $('#notice').hidden = false;
  if (!question) { $('#notice').textContent = 'Enter a question first.'; return; }
  const version = requestVersion;
  controller = new AbortController();
  const activeController = controller;
  const timer = setTimeout(() => activeController.abort(), 600000);
  $('#question-form button[type="submit"]').disabled = true;
  $('#notice').textContent = 'Retrieving evidence and generating your answer…';
  try {
    const response = await fetch('/api/qa', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question}), signal:controller.signal});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || 'The backend could not complete this question.');
    if (version !== requestVersion) return;
    if (!Array.isArray(payload.sources) || !Array.isArray(payload.paragraphs)) throw new Error('The backend returned an invalid answer.');
    liveResponse = payload;
    render();
    $('#notice').textContent = `Live response · ${payload.sources.length} evidence passages retrieved`;
  } catch (error) {
    if (version === requestVersion) $('#notice').textContent = error.name === 'AbortError' ? 'The request timed out. Please try again.' : `The QA service is unavailable. (${error.message})`;
  } finally {
    clearTimeout(timer);
    if (version === requestVersion) $('#question-form button[type="submit"]').disabled = false;
  }
}
function inspectSource(id) {
  document.querySelectorAll('.source-card').forEach(card => card.classList.remove('selected'));
  const card = document.getElementById(`source-${id}`);
  if (!card) return;
  card.classList.add('selected'); card.querySelector('details').open = true;
  card.scrollIntoView({behavior:'smooth',block:'center'}); card.focus({preventScroll:true});
}
document.addEventListener('click', event => {
  const modeButton = event.target.closest('[data-mode]');
  if (modeButton) { mode = modeButton.dataset.mode; render(); }
  const exampleButton = event.target.closest('[data-example]');
  if (exampleButton) loadExample(exampleButton.dataset.example);
  const citation = event.target.closest('[data-source]');
  if (citation) inspectSource(citation.dataset.source);
});
$('#question-form').addEventListener('submit', submitQuestion);
$('#new-question').addEventListener('click', () => {clearRequest(); $('#question').value = ''; $('#question').focus(); $('#notice').hidden = true;});
$('#show-evidence').addEventListener('click', () => {$('#evidence').scrollIntoView({behavior:'smooth'}); $('#evidence').focus({preventScroll:true});});
render();

if (document.modelContext?.registerTool) {
  const lifecycle = new AbortController();
  const tools = [
    {name:'clarivue_set_explanation_mode', description:'Change the explanation view of the current answer.', inputSchema:{type:'object', properties:{mode:{type:'string',enum:['everyday','learner','clinical']}},required:['mode'],additionalProperties:false}, execute:({mode:next})=>{if (!['everyday','learner','clinical'].includes(next)) throw new Error('Unknown mode'); mode=next; render(); return {mode};}},
    {name:'clarivue_load_example',description:'Fill an example question for submission to the research backend.',inputSchema:{type:'object',properties:{example:{type:'string',enum:['running','angina']}},required:['example'],additionalProperties:false},execute:({example})=>{loadExample(example); return {question:questions[example]};}}
  ];
  for (const tool of tools) {try {Promise.resolve(document.modelContext.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});} catch {}}
  window.addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
}
