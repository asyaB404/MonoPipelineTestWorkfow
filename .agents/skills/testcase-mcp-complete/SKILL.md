---
name: testcase-mcp-complete
description: 通过线上 MCP 端点（testcase-qa.cyouqa.com）执行：列游戏 → 上传需求文档 → 提交分析 → 轮询进度 → 导出 xlsx。把 session/认证/SSE 解析/token 节流都封装好，避免重复踩坑。触发词：生成测试用例、用 testcase-mcp、上传需求到 MCP、导出用例。
category: testcase
---

# TestCase MCP — Agent 执行手册（实战版）

## Skill 时间记录（强制）

遵守 `../functiontest-report-json/references/skill-timing-contract.md`。开始初始化 MCP 会话前，调用 `../functiontest-report-json/scripts/skill_timing.py start`；导出并确认测试用例文件落盘后调用 `end`。单独调用时使用本轮 operation 目录下的 `*-skill-timing.json`，作为根 Skill 按规则扣除环境过滤时间；由 workflow 调用时使用 workflow 传入的 timing 文件和 `parent_invocation_id`，只记录自己的原始起止时间，不扣除会话环境变量，由父 workflow 在最终上报时统一扣除。由 workflow 调用时只记录时间，不单独生成或上传 JSON。

实战 + 排坑沉淀的端到端 SOP。按 5 步走，每步直接复制可执行。

## 0. 准备（每一步都要用到）

### 0.1 端点 & 鉴权

```
BASE   = https://testcase-qa.cyouqa.com/mcp
AUTH   = Bearer t3st-c4se-mcp-2026
```

**关键事实**：这是标准的 **MCP HTTP+SSE + JSON-RPC** 端点，**不是**原 skill 写的 `/mcp/tools/call` REST 风格。调用方式是 `POST /mcp`，body 是 JSON-RPC `{"jsonrpc":"2.0","id":..,"method":"tools/call","params":{"name":..,"arguments":..}}`。

### 0.2 必带 headers

```
Authorization: Bearer <token>
Content-Type:  application/json
Accept:        application/json, text/event-stream
Mcp-Session-Id: <session id>     ← 第二步起必带
```

### 0.3 MCP 会话生命周期（每次新 bash 都要重新 init）

1. `initialize`（id=1） → 从响应头 `mcp-session-id:` 取 **SID**
2. `notifications/initialized`（无 id，不期待返回）
3. `tools/list`（可选：调试时看下有哪些工具）
4. 之后所有 `tools/call` 都要带 `Mcp-Session-Id: SID`

> ⚠ Bash 工具每次调用都是新进程。SID 用 `/tmp/mcp_sid.txt` 串起来，或者把整段流程塞进**同一个 bash 脚本**里。

### 0.4 Token 节流护栏

- 每次 MCP 调用 ≈ 几百 tokens 响应解析
- 轮询 **每 10 秒** 一次（用户节奏）
- **卡 `QUEUED_POINTS` > 5 分钟立刻停轮询**，报告故障，不要让 token 雪崩
- 完成后立刻退出轮询

---

## 1. 列游戏选 ID — `list_games`

**调用**：

```json
{"name": "list_games", "arguments": {}}
```

**返回**：`[{id, game_id, game_code, game_name, game_type, status, ...}, ...]`

**操作**：

- 把 10 个游戏以表格形式列给用户（含 game_name / game_type / 已有用例数 / 已有要点数）
- 让用户选 game_id（本项目是 CardFrame 塔防，最贴合"进击吧坦克" id=2 / 8711 / TOWER_DEF；用户上次选了 Party id=8 / 8694）
- ⚠ 用户选定的 game_id 即使类型不完全匹配，也要按用户选择走

---

## 2. 上传文档 — `upload_document`

**调用**：

```json
{
  "name": "upload_document",
  "arguments": {
    "file_name": "英雄列表界面设计文档.docx",
    "file_content_base64": "<整个 docx 的 base64>",
    "game_id": "8694",
    "game_type": "TOWER_DEF"
  }
}
```

**返回**：`{success: true, document_id: 674, file_name: "..", status: "PENDING"}`

**关键点**：

- `file_name` **必须带扩展名**（`.docx` / `.xlsx` / `.md` / `.txt`）— 服务端按扩展名解析类型
- `file_content_base64` 是整个文件的 base64 编码（不需要 chunk）
- 23 KB 的 docx 在 30s 内可上传完成；百 MB 级文档可能要分段或预压缩
- 中文字段在 SSE 响应 raw 里可能显示乱码（GBK→UTF-8 错位），不影响 server 内部存储；**靠 `document_id` 关联**即可
- Python 端用 `json.dumps(..., ensure_ascii=False)`

---

## 3. 提交分析 — `analyze_document`

**调用**：

```json
{
  "name": "analyze_document",
  "arguments": {"document_id": 674, "mode": "standard"}
}
```

**mode**：
- `"standard"`：标准覆盖维度（推荐）
- `"divergent"`：发散模式

**返回**：`{success: true, queued: true, document_id: 674, generation_round: 1, message: "..."}`

**关键点**：

- analyze **会立刻返回**（不入数据库等），实际处理在 Celery 后台
- `generation_round` 从 1 开始（每次重新 analyze 累加）
- analyze 之后 status 从 `PENDING` 推进到 `QUEUED_POINTS`

---

## 4. 轮询进度 — `get_progress`（每 10s）

**调用（单文档）**：

```json
{"name": "get_progress", "arguments": {"document_id": 674}}
```

**调用（全局队列）**：

```json
{"name": "get_progress", "arguments": {"game_id": "8694"}}
```

**返回字段**：

| 字段 | 说明 |
|------|------|
| `status` | queued / processing / completed / failed |
| `current_phase` | QUEUED_POINTS / GENERATING_POINTS / POINTS_COMPLETED / PROCESSING / COMPLETED |
| `progress` | 仅 processing 态有 |
| `queue_position` | 仅 processing 态有 |
| `estimated_remaining` | 仅 processing 态有 |

### 阶段映射

```
upload(PENDING) -> analyze(QUEUED_POINTS) 
   -> worker 消费 + 推 KB(GENERATING_POINTS)
   -> KB 抽取要点(POINTS_COMPLETED)
   -> 用例生成中(PROCESSING)
   -> 完成(COMPLETED)
```

### 轮询脚本模板

```bash
python - <<'PYEOF'
import json, urllib.request, time, re, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://testcase-qa.cyouqa.com/mcp'
AUTH = 'Bearer t3st-c4se-mcp-2026'
sid  = open('/tmp/mcp_sid.txt').read().strip()
did  = int(open('/tmp/mcp_did.txt').read().strip())

def call(name, args):
    payload = {"jsonrpc":"2.0","id":int(time.time()*1000)%1_000_000,
               "method":"tools/call","params":{"name":name,"arguments":args}}
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE, data=body, method='POST')
    req.add_header('Content-Type','application/json')
    req.add_header('Accept','application/json, text/event-stream')
    req.add_header('Authorization', AUTH)
    req.add_header('Mcp-Session-Id', sid)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')

t0 = time.time()
for i in range(60):  # 上限 60 * 10s = 10min（工具硬上限）
    body = call('get_progress', {'document_id': did})
    for line in body.split('\n'):
        if line.startswith('data:'):
            j = json.loads(line[5:].strip())
            inner = json.loads(j['result']['content'][0]['text'])
            elapsed = int(time.time() - t0)
            print(f"[{elapsed:>3}s]#{i+1:02d} status={inner.get('status')} "
                  f"phase={inner.get('current_phase')} "
                  f"prog={inner.get('progress','-')}% "
                  f"qpos={inner.get('queue_position','-')} "
                  f"eta={inner.get('estimated_remaining','-')}")
            if inner.get('status') in ('completed','failed'):
                sys.exit(0)
            break
    time.sleep(10)
else:
    print("[warn] 10 min 未结束，停下来报告状态")
PYEOF
```

### 故障排查（按当前_phase 判）

| 现象 | 根因 | 处理 |
|------|------|------|
| 卡 `QUEUED_POINTS` > 5min | Celery worker 未起 / 挂了 | 停轮询，报告运维；token 节流 |
| `kb_upload_status=NONE` | KB 没送到 | worker 整条死 |
| `progress`/`queue_position`/`estimated_remaining` 全 `-` | 还在 queued 态 | 等 worker 拉起 |
| `status=failed` + `error_message` | LLM 报错 | 看错误码；转本地 testcase-generator skill |

诊断 fallback：再调 `get_document_status` 看 `kb_upload_status` / `processed_at` / `error_message` 三件套交叉验证。

---

## 5. 完成后导出 xlsx — `export_test_cases`

**仅在 `status=COMPLETED` 后调用**。

**调用**：

```json
{"name": "export_test_cases", "arguments": {"document_id": 674}}
```

**返回**：

```json
{
  "success": true,
  "document_id": 674,
  "file_name": "test_cases_document_674.xlsx",
  "xlsx_base64": "UEsDBBQAAAAIA..."
}
```

### 落盘路径

```
<project_root>\Doc\AI开发文档\input\<feature_en>-testcases\<feature_en>-testcases-<seq4>\<file_name>
```

- `feature_en` 是英文小写下划线分隔（如 `hero-list` / `formation` / `battle`）
- file_name 取响应里的 `file_name`，一般是 `test_cases_document_<id>.xlsx`
- `seq4` 是 4 位递增编号。默认永远扫描 `Doc/AI开发文档/input/{feature_en}-testcases/` 下已有 `{feature_en}-testcases-####` 目录，取最大编号 +1；只有用户明确要求复用/覆盖某个测试用例目录时，才允许写入已有目录。
- 不得把质量部 MCP 导出的测试用例写到 `Doc/AI开发文档` 根目录或 output 目录。

### 落盘代码

```python
import base64, os, json, re
def parse_sse_first_json(s):
    for line in s.split('\n'):
        if line.startswith('data:'):
            return json.loads(line[5:].strip())
    return None

data = parse_sse_first_json(resp)
result = json.loads(data['result']['content'][0]['text'])
out_dir = r'Doc/AI开发文档/input/hero-list-testcases/hero-list-testcases-0001'
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, result['file_name'])
with open(out_path, 'wb') as f:
    f.write(base64.b64decode(result['xlsx_base64']))
print('saved:', out_path, os.path.getsize(out_path), 'bytes')
```

### 给用户的"下载路径"

- MCP **没有公开 URL**（接口只返 base64）
- 直接把项目根目录下的**相对路径**贴给用户作为文件位置：

```
Doc/AI开发文档/input/hero-list-testcases/hero-list-testcases-0001/test_cases_document_674.xlsx
```

- 用户打开方式：在项目根目录下使用资源管理器、`start "" "<path>"` 或 VSCode 打开

---

## 单独调用后的 JSON 上报

当用户直接调用 testcase-mcp-complete，而不是由 functiontest-workflow 编排时，导出测试用例并确认落盘后，必须自动完成一次用量上报：

1. 调用 check-cyoucode-spend 读取当前 Token 和消耗。
2. 调用 functiontest-report-json 的 operation-only 模式，固定操作类型为“质量部生成用例”，同时传入本轮已闭合的 timing 文件和 `--skill-name testcase-mcp-complete`，输出到本轮新的 operation 运行目录。
3. 调用 functiontest-json-upload 上传最终 JSON。

operation-only JSON 不读取测试报告，pass、failed、blocked、test_inconclusive、success_count、failure_count、bug_count 和 feature_count 等测试统计全部为 0，只写入操作类型、Token 和消耗数据。若 testcase-mcp-complete 是由 functiontest-workflow 调用，则不在此处重复上传，由主动测试工作流统一使用“主动测试工作流”上报。

示例输出路径：

```text
Doc/AI开发文档/output/{feature_en}/{feature_en}-operation-{seq4}/{feature_en}-operation-{seq4}-functiontest-upload.json
```

## 附录 A：常见坑

### A.1 Bash 每次调用是新进程

- SID 要么靠 `/tmp/mcp_sid.txt` 传（每次新 bash 都重新 init 一次）
- 要么把整段流程塞进**同一个 bash 脚本**

### A.2 响应是 SSE 不是纯 JSON

```
event: message
data: {"jsonrpc":"2.0", ...}


```

按 `split('\n')` 找含 `data:` 的行解 JSON。

### A.3 Windows Git Bash 编码

- stdout 默认 GBK，`print("中文")` 要 `sys.stdout.reconfigure(encoding='utf-8')`
- emoji/unicode 字符会炸，纯 ASCII 优先

### A.4 `python3` 不存在

- 此环境只有 `python`（Python 3 windows launcher 缺省名）
- inline heredoc：`python - "$@" <<'PYEOF'`

### A.5 /tmp 不是真会话内持久

- 每个新 bash session 的 `/tmp` 是干净的（虽然通常路径仍在）
- 跨 bash 假设 `/tmp` 持久**不安全**，每步脚本自带"读 / 不存在就重新 init"

### A.6 Python heredoc + `${VAR}` 展开

- 在 `<<'PYEOF'`（带引号）下 `${VAR}` **不展开** —— 改用 `<<PYEOF`（无引号）或在 heredoc 内 hardcode
- 注：本文档示例都用 hardcode 路径，避开坑

---

## 附录 B：兜底降级

| 场景 | 降级方案 |
|------|----------|
| MCP 服务不可用 | 改用本地 `testcase-generator` skill（CLAUDE.md 已推荐），输出 JSON + 染色 Excel + Markdown 完全一致 |
| 卡 QUEUED_POINTS 太久 | 不要继续轮询，找运维重启 Celery worker |
| token 耗尽 | 立刻停下报告进度，让用户决定，不要硬撑 |
| xlsx 巨大 | 分片导出（目前接口不支持，预留）|

---

## 附录 C：常用常量 & 工具速查

```
BASE              = https://testcase-qa.cyouqa.com/mcp
AUTH              = Bearer t3st-c4se-mcp-2026
POLL_INTERVAL     = 10s
MAX_POLL_SECONDS  = 600s (Bash 工具硬上限)
DEFAULT_OUT_DIR   = <project_root>/Doc/AI开发文档/input/<feature_en>-testcases/<feature_en>-testcases-<seq4>/
SHEET_PATH_TMP    = /tmp/mcp_sid.txt  /tmp/mcp_did.txt
```

### 工具清单（按使用顺序）

| # | 工具 | 何时用 |
|---|------|--------|
| 0 | `initialize` | 每个会话开始 |
| 0 | `notifications/initialized` | initialize 后立刻发 |
| 1 | `list_games` | 选 game_id |
| 2 | `upload_document` | 拿到 document_id |
| 3 | `analyze_document` | 提需求给后台 |
| 4 | `get_progress` | 10s 轮询直到 completed/failed |
| 4b | `get_document_status` | 排查 stalled 任务时交叉验证 |
| 5 | `export_test_cases` | COMPLETED 后导出 xlsx |
| 5b | `get_generated_test_cases` | 调试看 list（注意：可能与 xlsx 数据不完全一致）|

---

## 附录 D：一次完整实战样例（cardframe 英雄列表）

```
1. list_games                                    -> 10 个游戏，让用户选
2. user 选 Party (id=8, game_id=8694)           
3. upload_document(file=英雄列表界面设计文档.docx, game_id=8694, game_type=TOWER_DEF)
   -> document_id = 674, status=PENDING
4. analyze_document(document_id=674, mode=standard)
   -> queued=true, generation_round=1
5. get_progress(document_id=674) 每 10s 轮询
   - 18:03-18:19: 卡 QUEUED_POINTS 16min（worker 没起）
   - 18:21-18:51: worker 跑完 KB，进 PROCESSING 80%
   - 跨夜: 完成到 COMPLETED
6. export_test_cases(document_id=674)
   -> xlsx_base64 (71KB) -> 解码落盘 53KB
   -> Doc/AI开发文档/input/hero-list-testcases/hero-list-testcases-0001/test_cases_document_674.xlsx
```

总耗时 ~16h（含跨夜），其中 **16 分钟是 worker 故障等待**，**剩余是有效生成**。

---

## 附录 E：相关入口

- 本地生成 skill：`../testcase-gen/SKILL.md`（兜底用）
- 项目 Skill 入口说明：由当前 Skill 根目录提供
- 输入归档根：`Doc/AI开发文档/input/{feature_id}-testcases/{feature_id}-testcases-{seq4}/`
