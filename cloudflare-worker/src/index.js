export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: corsHeaders(),
      });
    }

    const url = new URL(request.url);
    const targetUrl = `${env.API_TARGET}${url.pathname}${url.search}`;

    const headers = new Headers(request.headers);
    headers.delete("host");

    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.method !== "GET" && request.method !== "HEAD" ? request.body : null,
    });

    const newResponse = new Response(response.body, response);
    for (const [key, value] of Object.entries(corsHeaders())) {
      newResponse.headers.set(key, value);
    }
    return newResponse;
  },
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Telegram-Init-Data",
    "Access-Control-Max-Age": "86400",
  };
}
