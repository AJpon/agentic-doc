export const meta = {
  name: 'wiki-run',
  description: 'agentic-doc: run outline, sync or audit of the codebase wiki in parallel',
  whenToUse:
    'Started by the agentic-doc wiki skill with args {mode, plugin_root, ...}. Do not start it directly: the skill passes plugin_root.',
  phases: [
    { title: 'Plan', detail: 'decide the target pages with the plan script' },
    { title: 'Research', detail: 'read the sources of each page' },
    { title: 'Write', detail: 'write each page' },
    { title: 'Verify', detail: 'two lenses try to refute citations and claims' },
    { title: 'Fix', detail: 'fix blocker and major findings (2 rounds at most)' },
    { title: 'Record', detail: 'checkpoint verified pages, save unresolved findings' },
    { title: 'Integrate', detail: 'table of contents, links, post_commands' },
    { title: 'Areas', detail: 'split the repository into survey areas' },
    { title: 'Survey', detail: 'survey each area' },
    { title: 'Propose', detail: 'three structure proposals (layer, flow, audience)' },
    { title: 'Merge', detail: 'merge the proposals and install the catalogue' },
    { title: 'Drift', detail: 'check whether changed pages still match the code' },
  ],
}

// Control only. Every procedure, prompt and rule lives in skills/wiki/references/; schemas live in
// skills/wiki/schemas/ and are embedded below by dev/embed_schemas.py.
// Top-level constants must stay above the mode dispatch: const is not hoisted.

// BEGIN GENERATED SCHEMAS (dev/embed_schemas.py)
const SCHEMAS = {"command-result":{"description":"Exit code and verbatim output of one command (step-command)","type":"object","required":["exit_code","stdout","stderr"],"properties":{"exit_code":{"type":"integer"},"stdout":{"type":"string"},"stderr":{"type":"string"}}},"drift":{"description":"Whether a changed page still matches the code (audit-drift)","type":"object","additionalProperties":false,"required":["page_id","issues"],"properties":{"page_id":{"type":"string"},"issues":{"type":"array","items":{"type":"object","required":["severity","location","problem","fix"],"additionalProperties":false,"properties":{"severity":{"type":"string","enum":["blocker","major","minor"]},"location":{"type":"string"},"problem":{"type":"string"},"fix":{"type":"string"},"lens":{"type":"string"}}}}}},"fix":{"description":"What a fix round changed or disputed (sync-fix)","type":"object","required":["changed","disputed"],"properties":{"changed":{"type":"array","items":{"type":"string"}},"disputed":{"type":"array","items":{"type":"string"}}}},"integrate":{"description":"Table of contents, links and post_commands (sync-integrate)","type":"object","required":["toc_files","links_fixed","broken_links_remaining","post_ran","post_passed","reverted"],"properties":{"toc_files":{"type":"array","items":{"type":"string"}},"links_fixed":{"type":"integer"},"broken_links_remaining":{"type":"array","items":{"type":"string"}},"post_ran":{"type":"boolean"},"post_passed":{"type":"boolean"},"reverted":{"type":"array","items":{"type":"string"}},"notes":{"type":"string"}}},"outline-result":{"description":"Result of merging the proposals and installing the catalogue (outline-merge)","type":"object","required":["installed","catalogue","page_count","rationale","issues"],"properties":{"installed":{"type":"boolean"},"catalogue":{"type":"string"},"page_count":{"type":"integer"},"rationale":{"type":"string"},"issues":{"type":"array","items":{"type":"string"}}}},"proposal":{"description":"One proposed wiki structure (outline-propose)","type":"object","required":["rationale","chapters","pages"],"properties":{"rationale":{"type":"string"},"chapters":{"type":"array","items":{"type":"object","required":["id","title","description"],"properties":{"id":{"type":"string"},"description":{"type":"string"}}}},"pages":{"type":"array","items":{"type":"object","required":["id","path","title","audience","brief","sources","related"],"properties":{"id":{"type":"string"},"path":{"type":"string"},"audience":{"type":"array","items":{"type":"string"}},"brief":{"type":"string"},"sources":{"type":"array","items":{"type":"string"}},"related":{"type":"array","items":{"type":"string"}}}}}}},"research":{"description":"Facts gathered for one page (sync-research)","type":"object","required":["page_id","note_path","key_claims"],"properties":{"page_id":{"type":"string"},"note_path":{"type":"string"},"key_claims":{"type":"array","items":{"type":"object","required":["claim","evidence"],"properties":{"claim":{"type":"string"},"evidence":{"type":"array","minItems":1,"items":{"type":"string"}}}}},"diagrams":{"type":"array","items":{"type":"object","required":["kind","subject"],"properties":{"kind":{"type":"string"},"subject":{"type":"string"}}}},"terms":{"type":"array","items":{"type":"string"}},"open_questions":{"type":"array","items":{"type":"string"}}}},"survey-areas":{"description":"How outline splits the repository for the survey (outline-areas)","type":"object","required":["areas"],"properties":{"areas":{"type":"array","minItems":3,"maxItems":5,"items":{"type":"object","required":["key","title","scope","questions"],"properties":{"key":{"type":"string","pattern":"^[a-z0-9][a-z0-9-]*$"},"scope":{"type":"array","items":{"type":"string"}},"questions":{"type":"array","items":{"type":"string"}}}}}}},"survey":{"description":"Findings about one area of the repository (outline-survey)","type":"object","required":["area","summary","findings"],"properties":{"area":{"type":"string"},"summary":{"type":"string"},"findings":{"type":"array","items":{"type":"object","required":["topic","detail","evidence"],"properties":{"topic":{"type":"string"},"detail":{"type":"string"},"evidence":{"type":"array","minItems":1,"items":{"type":"string"}}}}},"doc_gaps":{"type":"array","items":{"type":"string"}}}},"verdict":{"description":"Findings of one verification lens (verify-citation, verify-claim)","type":"object","required":["lens","pass","issues"],"properties":{"lens":{"type":"string","enum":["citation","claim"]},"pass":{"type":"boolean"},"checked_count":{"type":"integer"},"issues":{"type":"array","items":{"type":"object","required":["severity","location","problem","fix"],"additionalProperties":false,"properties":{"severity":{"type":"string","enum":["blocker","major","minor"]},"location":{"type":"string"},"problem":{"type":"string"},"fix":{"type":"string"},"lens":{"type":"string"}}}}}},"write":{"description":"What was written for one page (sync-write)","type":"object","required":["page_id","path","written"],"properties":{"page_id":{"type":"string"},"path":{"type":"string"},"written":{"type":"boolean"},"headings":{"type":"array","items":{"type":"string"}},"cited_files":{"type":"array","items":{"type":"string"}},"diagram_count":{"type":"integer"},"notes":{"type":"string"}}}}
// END GENERATED SCHEMAS

const PAGE_CHUNK_SIZE = 2 // pages in flight at once: at most PAGE_CHUNK_SIZE × 2 verify lenses
const MAX_FIX_ROUNDS = 2
const BLOCKING = ['blocker', 'major']
const ANGLES = ['layer', 'flow', 'audience']
const MECHANICAL = { model: 'haiku', effort: 'low' }

const opts = args || {}
if (!opts.plugin_root) {
  throw new Error('args.plugin_root is required (pass ${CLAUDE_PLUGIN_ROOT} from the wiki skill)')
}
const SKILL_DIR = opts.plugin_root + '/skills/wiki'

// ---------------------------------------------------------------- prompts and commands

function task(ref, inputs) {
  const read =
    ref === 'step-command.md'
      ? 'Read "' + SKILL_DIR + '/references/' + ref + '" and follow it exactly.'
      : 'Read "' + SKILL_DIR + '/references/common.md", then "' + SKILL_DIR + '/references/' + ref +
        '", and follow them exactly.'
  return [
    'You are one step of the agentic-doc wiki workflow. The repository root is the current directory.',
    'SKILL_DIR = ' + SKILL_DIR,
    read,
    'Inputs (JSON):',
    JSON.stringify(inputs),
  ].join('\n')
}

function quote(arg) {
  return /[\s"'$`\\]/.test(arg) ? '"' + arg.replace(/(["\\$`])/g, '\\$1') + '"' : arg
}

function cmd(...argv) {
  return ['uv run --script "' + SKILL_DIR + '/scripts/agentic_doc.py"'].concat(argv.map(quote)).join(' ')
}

async function runCommand(label, phaseName, command, file) {
  const input = file === undefined ? { command } : { command, file }
  return agent(task('step-command.md', input), {
    label,
    phase: phaseName,
    schema: SCHEMAS['command-result'],
    ...MECHANICAL,
  })
}

async function runPlan(planArgs) {
  const r = await runCommand('plan', 'Plan', cmd('plan', ...planArgs))
  if (!r) throw new Error('plan: the agent returned nothing')
  if (r.exit_code !== 0) throw new Error('plan failed (exit ' + r.exit_code + '): ' + r.stderr.trim())
  let plan
  try {
    plan = JSON.parse(r.stdout)
  } catch (e) {
    throw new Error('plan output is not JSON: ' + r.stdout.slice(0, 200))
  }
  if (!/^[0-9a-f]{40}$/.test(plan.head || '')) throw new Error('plan.head is not a 40-digit SHA: ' + plan.head)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(plan.today || '')) throw new Error('plan.today is not YYYY-MM-DD: ' + plan.today)
  // The plan output is transcribed by an agent; a dropped target would silently go unprocessed.
  if (!Array.isArray(plan.targets) || plan.targets.length !== plan.target_count) {
    throw new Error('plan transcription is incomplete: ' + (Array.isArray(plan.targets) ? plan.targets.length : 'no') +
      ' targets, target_count ' + plan.target_count)
  }
  const w = plan.warnings || {}
  if ((w.uncommitted || []).length) log('warning: uncommitted changes in sources: ' + w.uncommitted.join(', '))
  if ((w.untracked || []).length) log('warning: untracked files in sources: ' + w.untracked.join(', '))
  return plan
}

// ---------------------------------------------------------------- mode dispatch

const mode = opts.mode
if (mode === 'sync') return await runSync()
if (mode === 'outline') return await runOutline()
if (mode === 'audit') return await runAudit()
throw new Error('unknown mode: ' + mode + ' (outline | sync | audit)')

// ---------------------------------------------------------------- sync

function blocking(verdicts) {
  const out = []
  for (const v of verdicts) {
    for (const i of v.issues || []) {
      if (BLOCKING.includes(i.severity)) out.push({ ...i, lens: v.lens })
    }
  }
  return out
}

async function runVerify(page) {
  const verdicts = (
    await parallel(
      ['citation', 'claim'].map((lens) => () =>
        agent(task('verify-' + lens + '.md', { page }), {
          label: 'verify:' + lens + ':' + page.id,
          phase: 'Verify',
          schema: SCHEMAS.verdict,
        })
      )
    )
  ).filter(Boolean)
  if (verdicts.length < 2) {
    log(page.id + ': only ' + verdicts.length + '/2 verification lenses finished; the page stays unverified')
    return null
  }
  return verdicts
}

async function runSync() {
  const planArgs = []
  if (opts.pages && opts.pages.length) planArgs.push('--pages', ...opts.pages)
  if (opts.include_unresolved) planArgs.push('--include-unresolved')
  if (opts.today) planArgs.push('--today', opts.today)
  phase('Plan')
  const plan = await runPlan(planArgs)
  if (!plan.targets.length) {
    log('nothing to sync')
    return { mode: 'sync', head: plan.head, today: plan.today, pages: [], failed: [], skipped: plan.skipped || [], integrate: null }
  }
  log('targets (' + plan.targets.length + '): ' + plan.targets.map((t) => t.id).join(', '))

  // A page being rewritten is unverified until it passes review again; otherwise a rewrite that ends with
  // findings (or dies) would keep the old source_commit and still look fresh.
  const verified = plan.targets.filter((t) => t.source_commit).map((t) => t.id)
  if (verified.length) {
    const r = await runCommand('unverify', 'Plan', cmd('unverify', '--pages', ...verified))
    if (!r || r.exit_code !== 0) {
      throw new Error('unverify failed' + (r ? ' (exit ' + r.exit_code + '): ' + r.stderr.trim() : ''))
    }
  }

  // Research is the heaviest step, so a result that is still valid (same brief and same source contents)
  // is reused after an interruption. `plan` reports it per target in page.cache.
  async function saveCache(kind, page) {
    const r = await runCommand('cache:' + kind + ':' + page.id, 'Record', cmd('cache', 'save', kind, page.id))
    if (r && r.exit_code === 0) return true
    log(page.id + ': caching the ' + kind + ' result failed' + (r ? ' (exit ' + r.exit_code + '): ' + r.stderr.trim() : ''))
    return false
  }

  async function prepare(page) {
    if (page.pending > 0) {
      const r = await runCommand('findings:' + page.id, 'Research', cmd('findings', 'show', page.id))
      let saved = null
      try {
        saved = r && r.exit_code === 0 ? JSON.parse(r.stdout) : null
      } catch (e) {
        saved = null
      }
      if (Array.isArray(saved) && saved.length) {
        log(page.id + ': resuming from ' + saved.length + ' saved findings')
        return { resume: saved }
      }
    }
    const hit = page.cache || {}
    const researchHit = hit.research && hit.research.hit ? hit.research : null
    if (researchHit && hit.written && hit.written.hit) {
      log(page.id + ': the written page is still valid; going straight to verification')
      return { rewritten: true, notePath: researchHit.note_path }
    }
    if (researchHit) {
      log(page.id + ': reusing the cached research')
      return { researchPath: researchHit.path, notePath: researchHit.note_path }
    }
    const notePath = plan.work_dir + '/' + page.id + '/research.md'
    const research = await agent(task('sync-research.md', { page, note_path: notePath }), {
      label: 'research:' + page.id,
      phase: 'Research',
      schema: SCHEMAS.research,
    })
    if (!research) throw new Error('research failed: ' + page.id)
    if (!(await saveCache('research', page))) throw new Error('research result is not usable: ' + page.id)
    return { researchPath: plan.work_dir + '/' + page.id + '/research.json', notePath }
  }

  async function write(ctx, page) {
    if (ctx.resume || ctx.rewritten) return ctx
    const w = await agent(task('sync-write.md', { page, research_path: ctx.researchPath, note_path: ctx.notePath, today: plan.today }), {
      label: 'write:' + page.id,
      phase: 'Write',
      schema: SCHEMAS.write,
    })
    if (!w || w.written === false) throw new Error('write failed: ' + page.id)
    await saveCache('written', page)
    return { ...ctx, written: w.path }
  }

  async function record(page, findings) {
    const r = findings.length
      ? await runCommand('record:' + page.id, 'Record', cmd('findings', 'save', page.id, '<FILE>'), JSON.stringify(findings))
      : await runCommand('record:' + page.id, 'Record', cmd('checkpoint', '--pages', page.id, '--sha', plan.head, '--today', plan.today))
    if (!r || r.exit_code !== 0) {
      log(page.id + ': recording failed' + (r ? ' (exit ' + r.exit_code + '): ' + r.stderr.trim() : ''))
      return false
    }
    return true
  }

  async function verifyFixRecord(ctx, page) {
    const result = (kind, findings, disputed) => ({
      id: page.id,
      path: page.path,
      // A page resumed from saved findings is rewritten by fix, so it also goes to post_commands.
      written: ctx.written || (ctx.resume || ctx.rewritten ? plan.wiki_dir + '/' + page.path : null),
      result: kind,
      findings: findings.length,
      disputed,
    })
    const disputed = []
    let findings
    if (ctx.resume) {
      findings = ctx.resume.filter((i) => BLOCKING.includes(i.severity))
    } else {
      const verdicts = await runVerify(page)
      if (!verdicts) return result('unverified', [], disputed)
      findings = blocking(verdicts)
    }
    for (let round = 1; round <= MAX_FIX_ROUNDS && findings.length; round++) {
      log(page.id + ': fix round ' + round + '/' + MAX_FIX_ROUNDS + ' (' + findings.length + ' findings)')
      const input = { page, findings, round }
      if (ctx.notePath) input.note_path = ctx.notePath
      const fixed = await agent(task('sync-fix.md', input), {
        label: 'fix' + round + ':' + page.id,
        phase: 'Fix',
        schema: SCHEMAS.fix,
      })
      if (!fixed) log(page.id + ': the fix agent failed (round ' + round + ')')
      else disputed.push(...(fixed.disputed || []))
      await saveCache('written', page)
      const verdicts = await runVerify(page)
      if (!verdicts) return result('unverified', [], disputed)
      findings = blocking(verdicts)
    }
    const ok = await record(page, findings)
    if (findings.length) {
      log(page.id + ': ' + findings.length + ' findings remain')
      return result('unresolved', findings, disputed)
    }
    return result(ok ? 'verified' : 'unverified', [], disputed)
  }

  const results = []
  for (let i = 0; i < plan.targets.length; i += PAGE_CHUNK_SIZE) {
    const chunk = plan.targets.slice(i, i + PAGE_CHUNK_SIZE)
    log('batch ' + (i / PAGE_CHUNK_SIZE + 1) + '/' + Math.ceil(plan.targets.length / PAGE_CHUNK_SIZE) + ': ' + chunk.map((t) => t.id).join(', '))
    try {
      results.push(...(await pipeline(chunk, prepare, write, verifyFixRecord)))
    } catch (e) {
      log('batch failed: ' + (e && e.message ? e.message : String(e)))
    }
  }

  const pages = results.filter(Boolean)
  const failed = plan.targets.map((t) => t.id).filter((id) => !pages.some((p) => p.id === id))
  if (failed.length) log('failed pages: ' + failed.join(', '))

  let integrate = null
  if (pages.length) {
    phase('Integrate')
    integrate = await agent(
      task('sync-integrate.md', {
        pages: pages.map((p) => ({ id: p.id, path: p.path, result: p.result })),
        written_files: pages.map((p) => p.written).filter(Boolean),
      }),
      { label: 'integrate', phase: 'Integrate', schema: SCHEMAS.integrate }
    )
    if (!integrate) log('integrate failed: the table of contents, links and post_commands were not updated')
  }
  return {
    mode: 'sync',
    head: plan.head,
    today: plan.today,
    pages: pages.map((p) => ({ id: p.id, result: p.result, findings: p.findings, disputed: p.disputed })),
    failed,
    skipped: plan.skipped || [],
    integrate,
  }
}

// ---------------------------------------------------------------- outline

async function runOutline() {
  phase('Areas')
  const split = await agent(task('outline-areas.md', {}), {
    label: 'areas',
    phase: 'Areas',
    schema: SCHEMAS['survey-areas'],
  })
  if (!split || !split.areas.length) throw new Error('outline: the area split failed')

  phase('Survey')
  const surveys = (
    await pipeline(split.areas, (area) =>
      agent(task('outline-survey.md', { area }), { label: 'survey:' + area.key, phase: 'Survey', schema: SCHEMAS.survey })
    )
  ).filter(Boolean)
  if (!surveys.length) throw new Error('outline: no survey succeeded')
  log('surveys: ' + surveys.length + '/' + split.areas.length)

  phase('Propose')
  const proposals = (
    await parallel(
      ANGLES.map((angle) => () =>
        agent(task('outline-propose.md', { angle, surveys }), {
          label: 'propose:' + angle,
          phase: 'Propose',
          schema: SCHEMAS.proposal,
        })
      )
    )
  ).filter(Boolean)
  if (!proposals.length) throw new Error('outline: no proposal succeeded')

  phase('Merge')
  const merged = await agent(task('outline-merge.md', { surveys, proposals, force: !!opts.force }), {
    label: 'merge',
    phase: 'Merge',
    schema: SCHEMAS['outline-result'],
  })
  if (!merged) throw new Error('outline: the merge failed')
  return { mode: 'outline', ...merged }
}

// ---------------------------------------------------------------- audit

async function runAudit() {
  if (opts.lint_only) return { mode: 'audit', lint_only: true, drift: [], drift_failed: [] }
  phase('Plan')
  const plan = await runPlan([])
  const changed = plan.targets.filter((t) => t.state === 'changed')
  const drift = []
  const driftFailed = []
  if (changed.length) phase('Drift')
  for (let i = 0; i < changed.length; i += PAGE_CHUNK_SIZE) {
    const chunk = changed.slice(i, i + PAGE_CHUNK_SIZE)
    const results = await parallel(
      chunk.map((page) => () =>
        agent(task('audit-drift.md', { page }), { label: 'drift:' + page.id, phase: 'Drift', schema: SCHEMAS.drift })
      )
    )
    results.forEach((r, k) => {
      if (r) drift.push(r)
      else {
        log('drift check failed: ' + chunk[k].id)
        driftFailed.push(chunk[k].id)
      }
    })
  }
  return { mode: 'audit', lint_only: false, drift, drift_failed: driftFailed }
}
