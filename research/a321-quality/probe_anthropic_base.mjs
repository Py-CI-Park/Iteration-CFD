// Run with gui/node_modules/.bin/tsx.cmd research/a321-quality/probe_anthropic_base.mjs.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { createAnthropicClient } from "../../gui/server/src/agent/anthropic.ts";

const events = [
  { type: "message_start", message: { id: "msg_local", type: "message", role: "assistant",
    model: "local-fixture", content: [], stop_reason: null, stop_sequence: null,
    usage: { input_tokens: 1, output_tokens: 0 } } },
  { type: "content_block_start", index: 0, content_block: {
    type: "tool_use", id: "tool_local", name: "read_mesh_receipt", input: {} } },
  { type: "content_block_delta", index: 0, delta: { type: "input_json_delta", partial_json: '{"id":"fixture"}' } },
  { type: "content_block_stop", index: 0 },
  { type: "message_delta", delta: { stop_reason: "tool_use", stop_sequence: null }, usage: { output_tokens: 5 } },
  { type: "message_stop" },
];
let observed;
const fixture = createServer(async (req, res) => {
  let text = "";
  for await (const chunk of req) text += chunk;
  const body = JSON.parse(text);
  observed = { method: req.method, path: req.url, stream: body.stream,
    beta: Boolean(req.headers["anthropic-beta"]), fallbacks: body.fallbacks,
    thinking: body.thinking?.type, dummyCredentialOnly: req.headers["x-api-key"] === "local-fixture-only" };
  res.writeHead(200, { "content-type": "text/event-stream" });
  res.end(events.map(e => "event: " + e.type + "\ndata: " + JSON.stringify(e) + "\n\n").join(""));
});
await new Promise(resolve => fixture.listen(0, "127.0.0.1", resolve));
try {
  process.env.ANTHROPIC_BASE_URL = "http://127.0.0.1:" + fixture.address().port;
  process.env.ANTHROPIC_API_KEY = "local-fixture-only";
  delete process.env.ANTHROPIC_AUTH_TOKEN;
  const client = createAnthropicClient({ model: "local-fixture" });
  const stream = client.stream({ maxTokens: 128, effort: "medium", system: [],
    messages: [{ role: "user", content: "Synthetic loopback protocol probe." }],
    tools: [{ name: "read_mesh_receipt", input_schema: { type: "object", properties: { id: { type: "string" } } } }] });
  const response = await stream.finalMessage();
  assert.match(observed.path, /^\/v1\/messages(?:\?beta=true)?$/);
  assert.equal(observed.method, "POST");
  assert.equal(observed.stream, true);
  assert.equal(observed.dummyCredentialOnly, true);
  assert.equal(response.stop_reason, "tool_use");
  assert.deepEqual(response.content[0].input, { id: "fixture" });
  console.log(JSON.stringify({ ...observed, status: "PASS_LOCAL_FIXTURE",
    toolDecoded: true, toolExecuted: false, liveOpenCodex: false, externalRequest: false }));
} finally {
  await new Promise(resolve => fixture.close(resolve));
}
