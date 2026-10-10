// Workflow のスクリプトを、agent() などをスタブにして node で実行する（tests/test_workflow.py が使う）。
//
// 使い方: node workflow_harness.mjs <script.js> <scenario.json>
//
// scenario: {"args": any, "responses": [[ラベルの正規表現, 値], ...]}
//   - 値はそのまま agent() の戻り値になる。null はエージェントが死んだことを表す。
//   - {"__seq": [v1, v2, ...]} は呼ばれるたびに次の値を返す（最後の値を繰り返す）。
//   - {"__throw": "msg"} は agent() が例外を投げる。
//   - どの正規表現にも合わないラベルは例外になる（想定外の呼び出しをテストで検出するため）。
// 標準出力: {"calls": [...], "logs": [...], "result": any, "error": string|null, "max_in_flight": number}

import fs from 'node:fs'

const [scriptPath, scenarioPath] = process.argv.slice(2)
const source = fs.readFileSync(scriptPath, 'utf8').replace(/^export const meta\s*=/m, 'const meta =')
const scenario = JSON.parse(fs.readFileSync(scenarioPath, 'utf8'))
const responses = (scenario.responses || []).map(([pattern, value]) => ({ re: new RegExp(pattern), value, n: 0 }))
const calls = []
const logs = []
let inFlight = 0
let maxInFlight = 0

const tick = () => new Promise((resolve) => setTimeout(resolve, 0))

async function agent(prompt, opts = {}) {
  const label = opts.label || ''
  calls.push({
    label,
    phase: opts.phase || null,
    model: opts.model || null,
    effort: opts.effort || null,
    schema: opts.schema ? Object.keys(opts.schema.properties || {}) : null,
    prompt,
  })
  const r = responses.find((x) => x.re.test(label))
  if (!r) throw new Error('no response for label ' + label)
  inFlight++
  maxInFlight = Math.max(maxInFlight, inFlight)
  await tick()
  await tick()
  inFlight--
  let v = r.value
  if (v && typeof v === 'object' && !Array.isArray(v) && '__seq' in v) {
    v = v.__seq[Math.min(r.n, v.__seq.length - 1)]
    r.n++
  }
  if (v && typeof v === 'object' && !Array.isArray(v) && '__throw' in v) throw new Error(v.__throw)
  return v === undefined || v === null ? null : JSON.parse(JSON.stringify(v))
}

async function parallel(thunks) {
  return Promise.all(thunks.map((t) => Promise.resolve().then(t).catch(() => null)))
}

async function pipeline(items, ...stages) {
  return Promise.all(
    items.map(async (item, index) => {
      try {
        let prev = item
        for (const stage of stages) prev = await stage(prev, item, index)
        return prev
      } catch {
        return null
      }
    })
  )
}

const budget = { total: null, spent: () => 0, remaining: () => Infinity }
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor
const run = new AsyncFunction('agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', source)

let result = null
let error = null
try {
  result = await run(agent, parallel, pipeline, () => {}, (m) => logs.push(String(m)), scenario.args, budget)
} catch (e) {
  error = e && e.message ? e.message : String(e)
}
process.stdout.write(JSON.stringify({ calls, logs, result: result === undefined ? null : result, error, max_in_flight: maxInFlight }))
