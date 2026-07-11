// Lightweight readiness probe for the web container's Docker healthcheck
// (docker-compose.yml). Deliberately does no rendering or upstream calls so it
// reports the Next.js server process is accepting requests, which is what the
// rolling deploy (scripts/deploy.sh) gates the web rollout on.
export const dynamic = "force-dynamic";

export function GET() {
  return new Response("ok", {
    status: 200,
    headers: { "content-type": "text/plain" },
  });
}
