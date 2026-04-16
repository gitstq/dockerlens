<div align="center">

# 🔍 DockerLens

**Smart Dockerfile linter, analyzer & auto-fixer CLI**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-40%20passed-brightgreen.svg)]()

[English](#english) · [繁體中文](#繁體中文) · [日本語](#日本語)

18 条专业审查规则 · 自动修复 · 评分系统 · CI 集成 — 让你的 Dockerfile 从"能跑就行"变成"专业水准" 🚀

</div>

---

## 🎉 项目介绍

写完 Dockerfile 能跑就完事了？如果你遇到过以下问题——镜像 2GB+、容器被 OOMKill、安全扫描满屏红灯——那你需要 **DockerLens**。

DockerLens 是一个**有态度的** Dockerfile 审查工具，不仅告诉你哪里有问题，还会自动修复。

- 🔍 **18 条审查规则** — 覆盖安全、性能、可复现性、最佳实践四大维度
- 🔧 **7 条自动修复** — 一键修复 sudo、ADD→COPY、apt 缓存、exec form 等常见问题
- 📊 **评分系统** — 0-100 评分，一目了然你的 Dockerfile 健康度
- 🤖 **CI 集成** — `--ci` 模式，error 时返回非零退出码
- 📋 **规则列表** — `dockerlens rules` 查看所有规则及说明
- 🎨 **Rich 终端 UI** — 彩色输出，差量展示修复内容

**自研差异化亮点**：灵感来源于 [dockerfile-roast](https://github.com/immanuwell/dockerfile-roast)（Rust 写的 Dockerfile linter），但做了全面升级——Python 实现（零 Rust 工具链依赖）、17→18 条规则覆盖更全、7 条自动修复（原项目无修复能力）、0-100 评分系统、CI 友好的 JSON 输出与退出码、dry-run 安全预览模式。

## ✨ 核心特性

### 🔍 18 条审查规则

| ID | 严重级别 | 规则 | 自动修复 |
|----|---------|------|---------|
| DL0001 | ⚠️ Warning | 使用 `:latest` 标签 | ✅ |
| DL0002 | 🔴 Error | 以 root 用户运行 | — |
| DL0003 | ⚠️ Warning | apt 缓存未清理 | ✅ |
| DL0004 | 🔴 Error | 使用 sudo | ✅ |
| DL0005 | 🔵 Info | 应使用 COPY 替代 ADD | ✅ |
| DL0006 | ⚠️ Warning | 连续 RUN 应合并 | — |
| DL0007 | ⚠️ Warning | 缺少 HEALTHCHECK | — |
| DL0008 | 🔵 Info | 暴露特权端口 (1-1023) | — |
| DL0009 | 🔴 Error | ENV 中包含密钥/凭据 | — |
| DL0010 | 🔴 Error | 无效的 EXPOSE 端口 | — |
| DL0011 | ⚠️ Warning | 缺少 --no-install-recommends | ✅ |
| DL0012 | 🔵 Info | 缺少版本锁定 | — |
| DL0013 | ⚠️ Warning | ENTRYPOINT 使用 shell 格式 | ✅ |
| DL0014 | ⚠️ Warning | CMD 使用 shell 格式 | ✅ |
| DL0015 | 🔴 Error | 缺少 USER 指令 | — |
| DL0016 | 🔵 Info | FROM 镜像未锁定摘要 | — |
| DL0017 | ⚪ Style | WORKDIR 使用相对路径 | — |

### 🔧 自动修复

```bash
# 预览修复（安全模式）
dockerlens fix Dockerfile --dry-run

# 直接修复
dockerlens fix Dockerfile

# 修复到新文件
dockerlens fix Dockerfile -o Dockerfile.fixed
```

自动修复内容：
- `:latest` → `:stable`（建议手动确认版本号）
- `sudo` → 移除
- `ADD` → `COPY`（非 tar/URL 场景）
- apt 缓存清理 → 添加 `rm -rf /var/lib/apt/lists/*`
- `--no-install-recommends` → 自动添加
- Shell form ENTRYPOINT/CMD → Exec form

## 🚀 快速开始

### 环境要求

- Python 3.9+

### 安装

```bash
git clone https://github.com/gitstq/dockerlens.git
cd dockerlens
pip install -e .
```

### 基础使用

```bash
# 审查 Dockerfile
dockerlens lint Dockerfile

# 只检查错误级别
dockerlens lint Dockerfile --severity error

# 只运行特定规则
dockerlens lint Dockerfile --rules DL0001,DL0004,DL0015

# 输出 JSON（适合 CI/程序化处理）
dockerlens lint Dockerfile --json-output

# CI 模式（有 error 时退出码为 1）
dockerlens lint Dockerfile --ci

# 查看 Dockerfile 评分
dockerlens score Dockerfile

# 自动修复（预览）
dockerlens fix Dockerfile --dry-run

# 自动修复（应用）
dockerlens fix Dockerfile

# 查看所有规则
dockerlens rules
```

## 📖 详细使用指南

### 审查结果示例

对一个有问题的 Dockerfile 运行 `dockerlens lint`：

```
❌ Issues found — Dockerfile

┌───────┬──────────┬──────────┬──────────────────────────┬──────────────────────┐
│ Line  │ Severity │ Rule     │ Message                  │ Suggestion           │
├───────┼──────────┼──────────┼──────────────────────────┼──────────────────────┤
│ 1     │ warning  │ DL0001   │ Image 'ubuntu' uses      │ Replace with         │
│       │          │          │ implicit :latest tag     │ 'ubuntu:<version>'   │
│ 4     │ error    │ DL0004   │ Using sudo in Dockerfile │ Remove 'sudo'        │
│ 7     │ error    │ DL0009   │ Possible secret in ENV   │ Use Docker secrets   │
└───────┴──────────┴──────────┴──────────────────────────┴──────────────────────┘

  🔴 3 errors · 🟡 10 warnings · 🔵 5 info · ⚪ 1 style
  📊 Score: 0/100
```

### 评分系统

| 分数 | 含义 | 表情 |
|------|------|------|
| 90-100 | 优秀 | 🌟 |
| 70-89 | 良好 | 👍 |
| 50-69 | 需改进 | ⚠️ |
| 0-49 | 严重问题 | ❌ |

扣分规则：Error -15 / Warning -5 / Info -2 / Style -1

### CI 集成

```yaml
# GitHub Actions 示例
- name: Lint Dockerfile
  run: |
    pip install -e .
    dockerlens lint Dockerfile --ci --severity warning
```

`--ci` 模式下，发现 error 级别问题时返回退出码 1，CI 流水线会中断。

### JSON 输出

```bash
dockerlens lint Dockerfile --json-output
```

```json
{
  "file": "Dockerfile",
  "score": 55,
  "errors": 2,
  "warnings": 3,
  "issues": [
    {
      "rule_id": "DL0004",
      "severity": "error",
      "line": 4,
      "message": "Using sudo in Dockerfile is unnecessary",
      "suggestion": "Remove 'sudo' from the command"
    }
  ]
}
```

## 💡 设计思路与迭代规划

### 设计理念

- **有态度** — 规则不是"建议"，而是"你应该这么做"的专业判断
- **安全优先** — 密钥暴露、root 运行、特权端口等安全问题标记为 Error
- **自动修复** — 能自动修的不只报错，而是直接帮你改
- **CI 友好** — JSON 输出 + 退出码，无缝集成到流水线

### 后续迭代计划

- [ ] 📐 多阶段构建分析（跨阶段层数优化）
- [ ] 🖼️ 镜像大小估算（基于指令估算最终大小）
- [ ] 📊 历史评分趋势追踪
- [ ] 🔗 Docker Hub 镜像 digest 自动查询
- [ ] 📝 生成 Dockerfile 最佳实践报告（PDF/HTML）
- [ ] 🐳 Docker Compose 文件审查
- [ ] 🎯 .dockerignore 优化建议
- [ ] 🤖 LLM 驱动的智能修复建议

## 📦 安装与部署

### 从源码安装

```bash
git clone https://github.com/gitstq/dockerlens.git
cd dockerlens
pip install -e .
```

### 开发环境

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: add your feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

**新增 Lint 规则**：在 `dockerlens/rules/__init__.py` 中添加 `check_xxx` 函数，注册到 `ALL_RULES` 字典即可。如有自动修复，在 `dockerlens/fixer.py` 中添加对应 `fix_xxx` 函数。

## 📄 开源协议

本项目基于 [MIT 协议](LICENSE) 开源，可自由使用、修改和分发。

---

<a id="english"></a>

# 🔍 DockerLens

**Smart Dockerfile linter, analyzer & auto-fixer CLI**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-40%20passed-brightgreen.svg)]()

18 professional lint rules · Auto-fix · Scoring system · CI integration — Take your Dockerfile from "it works" to "it's professional" 🚀

## 🎉 Introduction

Finished writing your Dockerfile and called it a day? If you've ever dealt with 2GB+ images, OOMKilled containers, or security scan red alerts — you need **DockerLens**.

DockerLens is an **opinionated** Dockerfile linting tool that not only tells you what's wrong but also fixes it automatically.

- 🔍 **18 lint rules** — Covering security, performance, reproducibility, and best practices
- 🔧 **7 auto-fixes** — One-command fix for sudo, ADD→COPY, apt cache, exec form, and more
- 📊 **Scoring system** — 0-100 score for instant Dockerfile health check
- 🤖 **CI integration** — `--ci` mode returns non-zero exit code on errors
- 🎨 **Rich terminal UI** — Colored output with diff-style fix previews

## ✨ Key Features

- 18 lint rules across 4 severity levels (Error / Warning / Info / Style)
- 7 auto-fix rules with dry-run preview
- 0-100 scoring system
- JSON output for CI/programmatic processing
- CI mode with proper exit codes
- Rule filtering by ID and severity
- Zero Rust toolchain dependency (pure Python)

## 🚀 Quick Start

```bash
git clone https://github.com/gitstq/dockerlens.git
cd dockerlens
pip install -e .

# Lint a Dockerfile
dockerlens lint Dockerfile

# Score a Dockerfile
dockerlens score Dockerfile

# Auto-fix (preview)
dockerlens fix Dockerfile --dry-run

# Auto-fix (apply)
dockerlens fix Dockerfile

# List all rules
dockerlens rules

# CI mode
dockerlens lint Dockerfile --ci --severity warning

# JSON output
dockerlens lint Dockerfile --json-output
```

## 💡 Design Philosophy & Roadmap

### Design Principles

- **Opinionated** — Rules are professional judgments, not just suggestions
- **Security-first** — Secrets exposure, root user, privileged ports marked as Errors
- **Auto-fix** — Don't just report, fix it
- **CI-friendly** — JSON output + exit codes for seamless pipeline integration

### Roadmap

- [ ] Multi-stage build analysis
- [ ] Image size estimation
- [ ] Score trend tracking
- [ ] Docker Hub digest auto-lookup
- [ ] Best practice report generation (PDF/HTML)
- [ ] Docker Compose file linting
- [ ] .dockerignore optimization suggestions

## 📦 Installation & Development

```bash
git clone https://github.com/gitstq/dockerlens.git
cd dockerlens
pip install -e .

# Development
pip install -e ".[dev]"
pytest tests/ -v
```

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m 'feat: add your feature'`
4. Push: `git push origin feature/your-feature`
5. Submit a Pull Request

**Adding new rules**: Add a `check_xxx` function in `dockerlens/rules/__init__.py`, register in `ALL_RULES`. For auto-fix, add `fix_xxx` in `dockerlens/fixer.py`.

## 📄 License

[MIT License](LICENSE)

---

<a id="繁體中文"></a>

# 🔍 DockerLens

**智慧 Dockerfile 程式碼審查、分析與自動修復 CLI 工具**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-40%20passed-brightgreen.svg)]()

18 條專業審查規則 · 自動修復 · 評分系統 · CI 整合 — 讓你的 Dockerfile 從「能跑就行」變成「專業水準」🚀

## 🎉 專案介紹

寫完 Dockerfile 能跑就完事了？如果你遇到過映像 2GB+、容器被 OOMKill、安全掃描滿屏紅燈——那你需要 **DockerLens**。

- 🔍 **18 條審查規則** — 覆蓋安全、效能、可重現性、最佳實踐四大維度
- 🔧 **7 條自動修復** — 一鍵修復 sudo、ADD→COPY、apt 快取、exec form 等常見問題
- 📊 **評分系統** — 0-100 評分，一目了然你的 Dockerfile 健康度
- 🤖 **CI 整合** — `--ci` 模式，error 時回傳非零退出碼

## 🚀 快速開始

```bash
git clone https://github.com/gitstq/dockerlens.git
cd dockerlens
pip install -e .

# 審查 Dockerfile
dockerlens lint Dockerfile

# 查看 Dockerfile 評分
dockerlens score Dockerfile

# 自動修復（預覽）
dockerlens fix Dockerfile --dry-run

# 自動修復（套用）
dockerlens fix Dockerfile

# 查看所有規則
dockerlens rules
```

## 💡 設計理念與迭代規劃

- **有態度** — 規則不是「建議」，而是「你應該這麼做」的專業判斷
- **安全優先** — 密鑰暴露、root 執行、特權埠等安全問題標記為 Error
- **自動修復** — 能自動修的不只報錯，而是直接幫你改
- **CI 友好** — JSON 輸出 + 退出碼，無縫整合到流水線

### 後續迭代計畫

- [ ] 多階段建構分析
- [ ] 映像大小估算
- [ ] 歷史評分趨勢追蹤
- [ ] Docker Hub 映像摘要自動查詢
- [ ] 最佳實踐報告生成（PDF/HTML）

## 🤝 貢獻指南

1. Fork 本儲存庫
2. 建立特性分支：`git checkout -b feature/your-feature`
3. 提交變更：`git commit -m 'feat: add your feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

## 📄 開源協議

本專案基於 [MIT 協議](LICENSE) 開源。

---

<a id="日本語"></a>

# 🔍 DockerLens

**スマート Dockerfile リンター・アナライザー・自動修正 CLI**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-40%20passed-brightgreen.svg)]()

18のプロフェッショナルリントルール · 自動修正 · スコアリングシステム · CI統合 — Dockerfileを「動く」から「プロフェッショナル」へ 🚀

## 🎉 紹介

Dockerfileを書いて終わり？2GB以上のイメージ、OOMKilledコンテナ、セキュリティスキャンの赤いアラートに悩んだことがあるなら — **DockerLens** が必要です。

- 🔍 **18リントルール** — セキュリティ、パフォーマンス、再現性、ベストプラクティスを網羅
- 🔧 **7つの自動修正** — sudo、ADD→COPY、aptキャッシュ、exec formなどをワンコマンド修正
- 📊 **スコアリング** — 0-100スコアでDockerfileの健全性を一目で把握
- 🤖 **CI統合** — `--ci`モードでエラー時に非ゼロ終了コードを返す

## 🚀 クイックスタート

```bash
git clone https://github.com/gitstq/dockerlens.git
cd dockerlens
pip install -e .

# Dockerfileをリント
dockerlens lint Dockerfile

# スコア確認
dockerlens score Dockerfile

# 自動修正（プレビュー）
dockerlens fix Dockerfile --dry-run

# 自動修正（適用）
dockerlens fix Dockerfile

# ルール一覧
dockerlens rules
```

## 🤝 コントリビュート

1. このリポジトリをフォーク
2. フィーチャーブランチを作成：`git checkout -b feature/your-feature`
3. 変更をコミット：`git commit -m 'feat: add your feature'`
4. プッシュ：`git push origin feature/your-feature`
5. Pull Request を提出

## 📄 ライセンス

[MIT ライセンス](LICENSE)のもとで公開されています。
