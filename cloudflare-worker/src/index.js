const ORIGIN = "https://social-hub-three-sigma.vercel.app";

export default {
  async fetch(request) {
    const incoming = new URL(request.url);
    const target = new URL(ORIGIN);

    target.pathname = incoming.pathname;
    target.search = incoming.search;

    const upstream = new Request(target.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "follow"
    });

    const response = await fetch(upstream);

    const headers = new Headers(response.headers);
    headers.set("X-Social-Hub", "Cloudflare");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers
    });
  }
};
