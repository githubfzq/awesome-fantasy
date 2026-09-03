#!/usr/bin/env node
// 扫描 docs 目录树中所有 ```mermaid 代码块，用 mermaid 9.3.0（与 CDN 同版本）
// 的 parser 校验语法。只要有一张图 Parse/Lexical 失败，对应页面在 docsify
// 里就可能整页空白（renderer 抛异常）。
//
// 依赖（一次性装好，路径可复用）：
//   mkdir -p /tmp/mmcheck && cd /tmp/mmcheck && npm init -y
//   npm i mermaid@9.3.0 jsdom
// 用法：
//   NODE_PATH=/tmp/mmcheck/node_modules node check_mermaid.js /path/to/docs
'use strict'

const fs = require('fs')
const path = require('path')

let mermaid
try {
  const { JSDOM } = require('jsdom')
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', { pretendToBeVisual: true })
  // Node 21+ 自带只读 global.navigator（strict mode 下直接赋值会抛错），用 defineProperty 兜底
  for (const [k, v] of [['window', dom.window], ['document', dom.window.document], ['navigator', dom.window.navigator]]) {
    try {
      global[k] = v
    } catch {
      Object.defineProperty(global, k, { value: v, configurable: true })
    }
  }
  mermaid = require('mermaid')
  mermaid.initialize({ startOnLoad: false })
} catch (e) {
  console.error('初始化失败: ' + (e && e.message ? e.message : e))
  console.error('缺少 mermaid@9.3.0 / jsdom。一次性安装：')
  console.error('  mkdir -p /tmp/mmcheck && cd /tmp/mmcheck && npm init -y')
  console.error('  npm i mermaid@9.3.0 jsdom')
  console.error('  NODE_PATH=/tmp/mmcheck/node_modules node ' + path.basename(process.argv[1]) + ' <docs-dir>')
  process.exit(2)
}

const root = process.argv[2]
if (!root) {
  console.error('usage: node check_mermaid.js <docs-dir>')
  process.exit(2)
}

function walk(dir) {
  let out = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || entry.name === 'node_modules') continue
    const p = path.join(dir, entry.name)
    if (entry.isDirectory()) out = out.concat(walk(p))
    else if (entry.name.endsWith('.md')) out.push(p)
  }
  return out
}

const BLOCK_RE = /```mermaid\n([\s\S]*?)```/g
let ok = 0
let failed = 0

for (const file of walk(path.resolve(root))) {
  const src = fs.readFileSync(file, 'utf-8')
  let match
  while ((match = BLOCK_RE.exec(src))) {
    try {
      mermaid.parse(match[1])
      ok++
    } catch (e) {
      failed++
      const mdLine = src.slice(0, match.index).split('\n').length
      console.log('FAIL ' + file + ' (md line ' + mdLine + '): ' + String(e.message || e).split('\n')[0])
    }
  }
}
console.log(ok + ' diagrams OK, ' + failed + ' failed')
process.exit(failed ? 1 : 0)
