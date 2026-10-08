// Markdown 中の ```mermaid ブロックを mermaid.parse で構文検査する（オフライン、ブラウザ不要）。
//
// 使い方:
//   node mermaid_check.mjs <resolve-dir> FILE.md [FILE.md ...]
//
// <resolve-dir> は mermaid と jsdom を解決するディレクトリ（その下の node_modules を使う。通常は wiki_dir）。
// 標準出力に JSON 配列 [{file, block_index, line, message}] を出す（block_index と line は 1 始まりで、
// line は開きフェンス ```mermaid の行）。構文エラーは「データ」なので、見つかっても終了コードは 0。
// 非 0 になるのは基盤の失敗（mermaid/jsdom が無い、入力ファイルを読めない、引数が足りない）だけ。

import fs from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const OPEN = /^\s*```mermaid\s*$/
const CLOSE = /^\s*```\s*$/

function infraFail(message) {
  process.stderr.write('mermaid_check: ' + message + '\n')
  process.exit(2)
}

// Markdown から mermaid ブロックを取り出す。line は開きフェンスの行（1 始まり）。
function extractBlocks(text) {
  const blocks = []
  let current = null
  text.split(/\r?\n/).forEach((raw, i) => {
    if (current === null) {
      if (OPEN.test(raw)) current = { line: i + 1, lines: [] }
    } else if (CLOSE.test(raw)) {
      blocks.push({ line: current.line, source: current.lines.join('\n') })
      current = null
    } else {
      current.lines.push(raw)
    }
  })
  return blocks
}

async function loadMermaid(resolveDir) {
  try {
    const requireFrom = createRequire(path.join(path.resolve(resolveDir), 'package.json'))
    const { JSDOM } = requireFrom('jsdom')
    const mermaidUrl = pathToFileURL(path.join(path.resolve(resolveDir), 'node_modules/mermaid/dist/mermaid.core.mjs')).href
    const dom = new JSDOM('<!doctype html><body></body>')
    globalThis.window = dom.window
    globalThis.document = dom.window.document
    return (await import(mermaidUrl)).default
  } catch (e) {
    infraFail('cannot load mermaid/jsdom from ' + resolveDir + ': ' + e.message)
  }
}

const [resolveDir, ...files] = process.argv.slice(2)
if (!resolveDir) infraFail('usage: node mermaid_check.mjs <resolve-dir> FILE.md [FILE.md ...]')
const mermaid = await loadMermaid(resolveDir)
const errors = []

for (const file of files) {
  let text
  try {
    text = fs.readFileSync(file, 'utf8')
  } catch (e) {
    infraFail('cannot read ' + file + ' (' + e.message + ')')
  }
  const blocks = extractBlocks(text)
  for (let i = 0; i < blocks.length; i++) {
    try {
      await mermaid.parse(blocks[i].source)
    } catch (e) {
      errors.push({
        file,
        block_index: i + 1,
        line: blocks[i].line,
        message: String(e && e.message ? e.message : e).split('\n').slice(0, 3).join(' / ').slice(0, 300),
      })
    }
  }
}

process.stdout.write(JSON.stringify(errors, null, 2) + '\n')
