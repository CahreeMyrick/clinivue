// Same response contract as the local Python proxy. Configure a reachable HTTPS
// research endpoint in the hosted runtime; localhost is not reachable from Sites.
const json = (payload, status = 200) => new Response(JSON.stringify(payload), {status, headers:{'content-type':'application/json; charset=utf-8'}});
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/health') return json({ok:true,service:'clarivue-qa',backend_configured:Boolean(env?.CLARIVUE_RAG_URL)});
    if (url.pathname === '/api/evidence') return json({sources:[],message:'Submit a question to retrieve evidence.'});
    if (url.pathname === '/api/qa') {
      if (request.method !== 'POST') return json({error:'method_not_allowed'},405);
      let body;
      try {body = await request.json();} catch {return json({error:'invalid_request',message:'A JSON question is required.'},400);}
      const question = typeof body?.question === 'string' ? body.question.trim() : '';
      if (!question || question.length > 1500) return json({error:'invalid_request',message:'question must contain 1 to 1500 characters'},400);
      if (!env?.CLARIVUE_RAG_URL) return json({error:'not_configured',message:'The research backend is not connected to this hosted app.'},503);
      try {
        const target = new URL(env.CLARIVUE_RAG_URL);
        if (target.protocol !== 'https:') throw new Error('Configure an HTTPS research endpoint.');
        const headers = {'content-type':'application/json'};
        if (env.CLARIVUE_RAG_TOKEN) headers.authorization = `Bearer ${env.CLARIVUE_RAG_TOKEN}`;
        const response = await fetch(target, {method:'POST',headers,body:JSON.stringify({question}),signal:AbortSignal.timeout(540000)});
        const payload = await response.json();
        return json(payload, response.ok ? 200 : 502);
      } catch {return json({error:'backend_unavailable',message:'The research backend could not complete this question.'},502);}
    }
    if (env?.ASSETS) return env.ASSETS.fetch(request);
    return json({error:'not_found'},404);
  }
};
