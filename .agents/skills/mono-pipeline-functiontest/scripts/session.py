"""创建日期：2026-10-26；作者：Cyou。
更新日期：2026-11-12；更新人：Codex；统一字段/属性读取，显式区分缺值与真实零值。
功能：持久逐条主动会话、合法前置/一次动作/新帧读取、原预期比较和唯一四状态 final。
参数：完整用例、显式目标/权限、每次当前 Agent 的新请求；不包含模型服务或静态全集计划。
"""
from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, cast

from .contracts import (
    SCHEMA, VERDICTS, PERMISSIONS, EnvironmentBlocked, FrozenSession, HostError, InputError, IntegrityError,
    JsonObject, JsonValue, Limits, SecretGuard, canonical, compare_values, digest, field_value,
    hash_value, identifier, integer, keys_only, local_path, object_value, read_regular, scalar,
    strict_json, text, reject_links,
)
from .evidence import (
    INTERRUPTION_SUMMARY_NAME, Journal, case_directory, new_id, protected_file, record_data, record_int, run_path_budget, write_new,
)
from .inputs import CaseInput, OriginalCase, SourceItem, TargetConfig, bind_workflow, case_index, parse_cases, parse_provenance, parse_target, verify_workflow
from .pipeline import EvalReceipt, IdentityHooks, LocalHttp, Pipeline, Transport, observed_value, wrap_script, wrapper_format

CONTROL_CASE = "@session"
CHAIN_SCHEMA = "mono-pipeline-chain/1"
READ_PURPOSES = frozenset({"discovery", "precondition", "guard", "before", "after", "step", "logs"})
# 设备侧命名观测 op：Agent 只传参数、不写 C#，一次调用取回结构化业务事实。
# 边界：只返回业务事实，绝不返回 success/assertion/passed/verdict；不替代原预期比较或独立新帧门禁。
BUILTIN_OBSERVATIONS: frozenset[str] = frozenset({"chain", "subtree", "buttons", "logic_field", "member_probe"})
BUILTIN_MAX_DEPTH = 6
BUILTIN_MAX_NODES = 3000
BUILTIN_MAX_MEMBERS = 32
BUILTIN_MAX_MEMBER_DEPTH = 8
OPERATIONS = frozenset({"attach", "status", "chain-start", "chain-end", "start-case", "observe", "action", "compare", "final", "attribute",
                        "baseline", "reference", "collect-evidence", "note", "close", "audit", "report"})
# 计划静态自检不是会话操作：不写业务事件、不建连、不消耗命令 ID，只在本地复用同一套静态预检。
PLAN_CHECK_SCHEMAS = frozenset({"plan", "suite"})
# 单例计划只允许在一条命令内串起本用例步骤；不含附加、关闭、审计与报告等跨例控制操作。
PLAN_OPERATIONS = frozenset({"start-case", "observe", "compare", "action", "final", "attribute", "note",
                             "baseline", "reference", "collect-evidence"})
PLAN_SCHEMA = "mono-pipeline-case-plan/1"
PLAN_KEYS = frozenset({"schema", "case_id", "group_id", "steps", "defaults"})
PLAN_STEP_KEYS = frozenset({"operation", "request"})
PLAN_STEP_LIMIT = 512
# 多例计划复用连接，证据仍按例私有；Player 的业务状态会延续，后续各例须独立核验前置。
SUITE_SCHEMA = "mono-pipeline-case-suite/1"
SUITE_KEYS = frozenset({"schema", "cases", "defaults"})
SUITE_CASE_KEYS = frozenset({"case_id", "group_id", "steps"})
SUITE_CASE_LIMIT = 64
SUITE_STEP_LIMIT = 4096
# 计划级共享声明：只覆盖批内完全一致的机械上下文（发送方式、当前唯一目标、只读/目标审核结论、理由），
# 不替代任何原文绑定、字段选择、操作符或独立预期，也不改变门禁。缺失字段才补，已写字段不被覆盖。
PLAN_DEFAULT_KEYS = frozenset({"send", "target", "value_format", "timeout_ms", "read_only_review",
                               "target_review", "reason"})
# 原步骤含明确交互动词时，读取不能代替动作覆盖；业务数量/状态名词不单独视为交互。
ACTION_STEP_PATTERN = re.compile(
    r"点击|点按|单击|双击|长按|拖动|滑动|选择(?!态|状态|情况|结果|标识|字段|属性|的(?:棋子|角色|道具|单位))|切换|提交|领取|升级|购买|保存|使用|兑换|装备|启动|"
    r"(?:^|[，,。；;]|并|然后|再|随后|接着|入口|按钮|页签|选项卡|功能|面板|页面|界面)\s*"
    r"(?:输入|打开|进入|退出|关闭|返回|前往|导航到|跳转到|切换到)|"
    r"\b(?:click|tap|press|drag|swipe|type|select|choose|toggle|switch|submit|claim|upgrade|purchase|save|use|activate|redeem|equip|trigger)\b|"
    r"(?:^|[.;,]|\bthen\b|\band\b)\s*(?:input|enter|exit|open|close|return|navigate|switch to)\b",
    re.IGNORECASE,
)
CONTEXTUAL_ACTION_STEP_PATTERN = re.compile(
    r"(?:执行|进行|发起|开始|触发)\s*(?:一次|单次|一轮)?(?:达到保底的)?(?:抽卡|抽取|祈愿|单抽|十连)|"
    r"(?:激活|启用)(?:目标|对应|该)?(?:功能|技能|账号|道具|入口|按钮)|"
    r"\b(?:perform|execute)\s+(?:one|a|an|single|ten)?\s*(?:draw|pull|gacha|wish)\b|"
    r"\b(?:draw|pull)\s+(?:once|one|ten|a single|a ten-pull)\b",
    re.IGNORECASE,
)
NEGATED_ACTION_PREFIX_PATTERN = re.compile(
    r"(?:并未|没有|无需|无须|不再|不要|不得|禁止|不能|不可|未曾|可以|可|不|未|没)"
    r"(?:(?:应该|需要|再|继续|进行|执行|发起|触发|任何|重复|主动|直接|操作|做){0,2})$"
    r"|(?:do not|does not|did not|never|without|not)\s*(?:(?:need to|have to|continue to|perform|execute)\s*){0,2}$",
    re.IGNORECASE,
)
NAVIGATION_ACTION_PATTERN = re.compile(
    r"(?:点击|点按|单击).{0,40}(?:入口|页签|选项卡|功能|页面|界面|面板)|"
    r"(?:打开|进入|前往|导航到|跳转到|切换到).{0,40}(?:功能|页面|界面|面板|模块|入口)|"
    r"\b(?:click|tap|open|enter|navigate to|go to)\b.{0,50}\b(?:entry|feature|module|page|screen|panel|menu)\b", re.IGNORECASE | re.DOTALL)


# 功能：判断原步骤是否明确要求交互；参数 value 为原文，不从预期或字段名推断动作。
def step_requires_action(value: str) -> bool:
    for pattern in (ACTION_STEP_PATTERN, CONTEXTUAL_ACTION_STEP_PATTERN):
        for match in pattern.finditer(value):
            prefix: str = value[max(0, match.start() - 24):match.start()]
            if NEGATED_ACTION_PREFIX_PATTERN.search(prefix) is None:
                return True
    return False
# 每个 operation 允许从计划级 defaults 继承的字段；未登记的操作不继承任何字段（compare/final 必须逐条判断）。
STEP_DEFAULT_FIELDS: dict[str, frozenset[str]] = {
    "observe": frozenset({"send", "target", "value_format", "timeout_ms", "read_only_review", "reason"}),
    "action": frozenset({"send", "target", "value_format", "timeout_ms", "target_review", "reason"}),
}
BUSINESS_EVENTS = frozenset({"case_started", "intent", "command_result", "comparison", "case_final",
                             "attribution", "baseline_registered", "reference_recorded", "artifact_collected",
                             "poll_started", "poll_closed", "case_note", "session_attached", "case_frozen",
                             "chain_started", "chain_closed"})
# 断言规则库：预先逐条审定的语义依据，供 compare 用 rule 简写替代两段自然语言论证；展开结果必须与手写完全等价。
# 收录边界：只收「字段名本身已完整表达语义、无需按用例再解释」的机械断言；任何需要业务口径判断的字段仍须手写 basis。
RULE_BASIS: dict[str, JsonObject] = {
    "star_node_zero": {
        "statement": "升星节点的空/亮资源名直接表示该星位是否点亮；Img_Empty 表示该星位未点亮（0 星）。",
        "semantic_review": "当前 Agent 已核对升星节点资源命名与配置：空节点名代表未点亮星位，与「0 星」原预期一致。",
    },
    "star_node_lit": {
        "statement": "升星节点点亮资源名表示该星位已点亮；非空点亮名表示对应星级已达成。",
        "semantic_review": "当前 Agent 已核对升星节点点亮语义：点亮资源名代表星位达成，与星级原预期一致。",
    },
    "button_active": {
        "statement": "GameButton 激活态字段直接表示按钮是否可点击；active=false 表示按钮未激活/置灰。",
        "semantic_review": "当前 Agent 已核对按钮激活字段语义：激活态代表可交互，与「按钮不可点击/置灰」原预期一致。",
    },
    "count_compare": {
        "statement": "计数类字段数值直接代表持有/需求数量，可按数值比较判断条件是否满足。",
        "semantic_review": "当前 Agent 已核对计数字段语义：数值直接对应持有量与需求量，与数量原预期一致。",
    },
    # 以下为本轮扩充：Unity 节点与文本的基础存在态断言，字段名即语义，不含业务数值口径。
    "node_active": {
        "statement": "GameObject.activeInHierarchy 直接表示该节点在层级中是否实际激活显示；true 表示节点可见且参与渲染。",
        "semantic_review": "当前 Agent 已核对节点激活字段语义：activeInHierarchy 是 Unity 引擎级事实，与「该区域/控件已显示」的原预期一致。",
    },
    "node_inactive": {
        "statement": "GameObject.activeInHierarchy 直接表示该节点在层级中是否实际激活显示；false 表示节点未显示。",
        "semantic_review": "当前 Agent 已核对节点激活字段语义：activeInHierarchy 为 false 即该节点及其子级不参与渲染，与「该区域/控件已隐藏」的原预期一致。",
    },
    "text_equals": {
        "statement": "GameText.text 是界面实际渲染的文本原值，可直接与需求或配置给出的完整文案逐字比对。",
        "semantic_review": "当前 Agent 已核对 GameText 文本字段语义：该字段即用户可见文案原值，与「界面文案应为指定内容」的原预期一致。",
    },
    "text_contains": {
        "statement": "GameText.text 是界面实际渲染的文本原值；原预期为文本包含关系时，可用包含比较判断关键词是否出现在实际文案中。",
        "semantic_review": "当前 Agent 已核对原预期确实只要求关键词出现而非整句相等，且 GameText 字段即用户可见文案，故采用包含比较而非整句相等。",
    },
    "sprite_loaded": {
        "statement": "GameImage.sprite 非空表示该图片节点已成功加载并绑定了实际图片资源；为空表示未加载或占位未赋值。",
        "semantic_review": "当前 Agent 已核对 GameImage 图片字段语义：sprite 非空即资源已实际绑定，与「图片/图标正常显示」的原预期一致。",
    },
    "toggle_on": {
        "statement": "GameToggle.isOn 直接表示该开关/页签控件当前是否处于选中态；true 为选中。",
        "semantic_review": "当前 Agent 已核对 GameToggle 选中字段语义：isOn 即控件选中状态，与「该页签/开关处于选中」的原预期一致。",
    },
    "toggle_off": {
        "statement": "GameToggle.isOn 直接表示该开关/页签控件当前是否处于选中态；false 为未选中。",
        "semantic_review": "当前 Agent 已核对 GameToggle 选中字段语义：isOn 为 false 即控件未选中，与「该页签/开关未选中」的原预期一致。",
    },
    "list_count": {
        "statement": "容器节点下生效子项数量可直接与配置或需求声明的条目数比较，判断列表/格子是否按预期生成。",
        "semantic_review": "当前 Agent 已核对容器子项计数语义：子项数量即实际生成的条目数，与「列表应生成 N 项」的原预期一致。",
    },
    # 以下为 2026-10-30 扩充：数值/等级/进度类机械断言，字段名即语义，不含业务口径判断。
    "number_equals": {
        "statement": "数值字段是界面或数据层的实际业务数值原值，可直接与需求或配置给出的精确数值逐值比较。",
        "semantic_review": "当前 Agent 已核对数值字段语义：该字段即业务数值原值，与「该数值应等于指定值」的原预期一致。",
    },
    "number_compare": {
        "statement": "数值字段是实际业务数值原值，可按大于/大于等于/小于/小于等于关系与需求声明的边界值比较。",
        "semantic_review": "当前 Agent 已核对数值字段语义并确认原预期为大小关系而非精确相等，故采用数值关系比较。",
    },
    "level_equals": {
        "statement": "等级字段是当前等级的实际数值原值，可直接与需求或配置声明的等级数值比较。",
        "semantic_review": "当前 Agent 已核对等级字段语义：该字段即当前等级，与「等级应为指定值」的原预期一致。",
    },
    "segment_count": {
        "statement": "进度/分段容器的生效分段节点数量即已完成或已生成的分段数，可直接与需求声明的分段数比较。",
        "semantic_review": "当前 Agent 已核对分段计数语义：分段节点数量即实际分段数，与「分段数应等于 N」的原预期一致。",
    },
    "interactable_state": {
        "statement": "按钮/控件可交互字段直接表示其当前是否可被点击；true 为可交互，false 为置灰或不可用。",
        "semantic_review": "当前 Agent 已核对可交互字段语义：该字段即控件可用状态，与「该控件可/不可点击」的原预期一致。",
    },
    "text_present": {
        "statement": "GameText.text 是界面实际渲染的文本原值；非空表示该文本节点已赋值并显示实际文案。",
        "semantic_review": "当前 Agent 已核对文本字段语义：非空即该文案节点已渲染实际内容，与「文案应存在且非空」的原预期一致。",
    },
}


# 功能：把计划级 defaults 合并进单步请求；参数 operation 决定可继承字段集，已写字段一律不被覆盖。
def apply_plan_defaults(operation: str, request: JsonObject, defaults: JsonObject) -> JsonObject:
    if not defaults:
        return request
    allowed: frozenset[str] | None = STEP_DEFAULT_FIELDS.get(operation)
    if allowed is None:
        # compare/final/start-case 等步骤必须逐条给出独立依据，不继承任何机械字段。
        return request
    merged: JsonObject = dict(request)
    for key in sorted(allowed):
        if key not in merged and key in defaults:
            merged[key] = defaults[key]
    return merged


# 功能：把 compare 的 rule 简写展开为完整 basis；参数 request 为原始比较请求，未使用 rule 时原样返回且幂等。
def expand_rule_basis(request: JsonObject) -> JsonObject:
    rule: JsonValue = request.get("rule")
    if rule is None:
        return request
    if not isinstance(rule, str) or rule not in RULE_BASIS:
        raise InputError("断言 rule 指向未审定规则；规则库未收录即拒绝")
    if "basis" in request:
        raise InputError("rule 简写与手写 basis 不能同时出现")
    for key in ("op", "target", "value"):
        if key not in request:
            raise InputError("rule 简写必须同时给出 op/target/value，不得只给规则名")
    operator: str = text(request["op"], "rule.op")
    if operator not in {"eq", "ne", "gt", "ge", "lt", "le", "contains", "delta"}:
        raise InputError("未知独立比较规则")
    rule_basis: JsonObject = RULE_BASIS[rule]
    expanded: JsonObject = {key: value for key, value in request.items() if key not in {"rule", "op", "target", "value"}}
    expanded["field"] = text(request["target"], "rule.target")
    expanded["operator"] = operator
    basis: JsonObject = {
        "kind": "literal", "value": request["value"], "reviewer": "current_agent",
        "statement": rule_basis["statement"], "semantic_review": rule_basis["semantic_review"],
    }
    # contains 的弱断言标记由规则库自身声明，调用方不必重复手写；其余规则保持严格标量比较。
    if operator == "contains":
        basis["original_is_text_contains"] = True
    expanded["basis"] = basis
    return expanded


# 功能：只检查字段路径语法和禁用的自述结论；参数 value 为 JSON Pointer，空串表示根值，不读取业务事实。
def check_pointer(value: JsonValue, label: str) -> str:
    if not isinstance(value, str) or (value and not value.startswith("/")) or re.search(r"~(?:[^01]|$)", value):
        raise InputError(label + " 必须为合法 JSON Pointer")
    if any(part.replace("~1", "/").replace("~0", "~").lower() in {"success", "assertion", "passed", "verdict"} for part in value.split("/")):
        raise InputError("比较不能采用脚本自述成功/断言字段")
    return value


# 功能：共用轮询条件校验；参数 value 为可选条件，after_command_id 绑定显式业务完成等待。
def poll_condition(value: JsonValue, after_command_id: JsonValue) -> JsonObject | None:
    if value is None:
        return None
    condition: JsonObject = object_value(value, "poll")
    keys_only(condition, {"field", "operator", "value", "stable_samples", "require_match"}, "poll", {"field", "operator", "value"})
    check_pointer(condition["field"], "poll.field")
    if text(condition["operator"], "poll.operator") not in {"eq", "ne", "gt", "ge", "lt", "le"}:
        raise InputError("轮询早停只能使用严格标量/数值比较")
    scalar(condition["value"])
    integer(condition.get("stable_samples", 1), "stable_samples", 1, 8)
    if type(condition.get("require_match", False)) is not bool:
        raise InputError("poll.require_match 必须为布尔值")
    if condition.get("require_match") is True and after_command_id is None:
        raise InputError("业务完成轮询必须显式关联 after_command_id")
    return condition


# 功能：解析 Agent 审阅的共享准备来源，不加入业务原全集；参数 request 保留准备步骤、预期和授权范围说明，limits 为原预算。
def parse_chain_source(request: JsonObject, limits: Limits) -> OriginalCase:
    keys_only(request, {"schema", "title", "preconditions", "steps", "expected", "reviewer", "review",
                        "capability_gate"},
              "chain source", {"schema", "title", "preconditions", "steps", "expected", "reviewer", "review"})
    if request["schema"] != CHAIN_SCHEMA or request["reviewer"] != "current_agent":
        raise InputError("共享链路必须来自当前 Agent 审阅的独立准备来源")
    text(request["review"], "chain review", trim=False)
    source: JsonObject = {**request, "case_id": CONTROL_CASE}
    original: OriginalCase = parse_cases(canonical(source), limits).cases[0]
    gate_value: JsonValue = request.get("capability_gate")
    if gate_value is not None:
        gate: JsonObject = object_value(gate_value, "capability_gate")
        keys_only(gate, {"name", "entry_path", "step_index", "expected_index", "ready_field"},
                  "capability_gate", {"name", "entry_path", "step_index", "expected_index", "ready_field"})
        name: str = text(gate["name"], "capability_gate.name")
        text(gate["entry_path"], "capability_gate.entry_path")
        step_index: int = integer(gate["step_index"], "capability_gate.step_index")
        expected_index: int = integer(gate["expected_index"], "capability_gate.expected_index")
        check_pointer(gate["ready_field"], "capability_gate.ready_field")
        step_text: str = original.item("step", step_index).text
        expected_text: str = original.item("expected", expected_index).text
        if not NAVIGATION_ACTION_PATTERN.search(step_text) or name.casefold() not in step_text.casefold() or name.casefold() not in expected_text.casefold():
            raise InputError("capability_gate 必须绑定包含目标名称的真实入口交互步骤及对应可用预期")
    return original


# 功能：在共享链路收口时核验 GM/准备动作之后的真实目标入口与可用态；参数 source 为原链路，item 为重建状态，commands 为本轮命令。
def chain_action_gate_error(source: OriginalCase, item: CaseState, commands: dict[str, JsonObject]) -> str | None:
    gate_value: JsonValue = source.raw.get("capability_gate")
    if not item.actions and gate_value is None:
        return None
    if gate_value is None:
        return "含准备动作的共享链路必须声明目标功能入口与可用态 capability_gate"
    gate: JsonObject = object_value(gate_value, "capability_gate")
    if not item.actions:
        return "共享链路声明了 capability_gate，但没有真实入口动作"
    field: str = str(gate["ready_field"])
    expected_index: int = integer(gate["expected_index"], "capability expected index")

    def ready_was_compared_after(action_id: str) -> bool:
        post_action_observations: set[str] = {
            observation_id for observation_id, observation in item.observations.items()
            if observation.get("valid") is True and observation.get("after_command_id") == action_id
        }
        for comparison in item.comparisons.values():
            binding: JsonObject = object_value(comparison.get("binding"), "capability ready comparison")
            basis: JsonObject = object_value(binding.get("basis"), "capability ready basis")
            if (comparison.get("valid") is True and comparison.get("matched") is True
                    and binding.get("scope") == "expected" and binding.get("index") == expected_index
                    and binding.get("field") == field and binding.get("operator") == "eq"
                    and binding.get("observation_id") in post_action_observations
                    and basis.get("kind") == "literal" and basis.get("value") is True):
                return True
        return False

    entry_action_ids: list[str] = []
    for action_id in item.actions:
        action_record: JsonObject | None = commands.get(action_id)
        if action_record is None:
            continue
        action: JsonObject = record_data(action_record)
        if action.get("scope") != "step" or action.get("index") != gate["step_index"]:
            continue
        original_ref: JsonObject = object_value(action.get("script_original"), "capability action source")
        action_source: JsonObject = object_value(original_ref.get("source"), "capability action metadata")
        options: JsonObject = object_value(action_source.get("options"), "capability action options")
        action_text: str = text(action.get("original_text"), "capability action text", trim=False)
        if (action_source.get("kind") == "builtin_action"
                and action_source.get("path") == "builtin:click_button"
                and options.get("path") == gate["entry_path"]
                and NAVIGATION_ACTION_PATTERN.search(action_text)):
            entry_action_ids.append(action_id)
    if len(entry_action_ids) != 1:
        return "共享链路必须恰有一次 capability_gate 指定目标入口的真实点击"
    entry_action_id: str = entry_action_ids[0]
    if not ready_was_compared_after(entry_action_id):
        return "目标入口动作后缺少新帧上的目标功能可用态原预期比较"
    last_action_id: str = item.actions[-1]
    if last_action_id != entry_action_id and not ready_was_compared_after(last_action_id):
        return "后续准备动作后缺少新帧上的目标功能最终可用态原预期比较"
    return None


# 功能：单请求和计划共用的提交前结构检查；参数 original 为完整原例、limits 为真实目标预算、base 为请求目录。
# 边界：不登记来源、不连接 Player、不预判业务通过；运行期仍核验实际 before、守卫、前置和新帧。
def check_request_contract(operation: str, request: JsonObject, original: OriginalCase | None,
                           limits: Limits, base: Path) -> None:
    SecretGuard().check(request)
    if operation in {"observe", "action"}:
        if text(request.get("send", "eval_file"), "send") not in {"eval", "eval_file"}:
            raise InputError("send 只能为 eval/eval_file")
        if text(request.get("value_format", "json"), "value_format") not in {"json", "bridge"}:
            raise InputError("实际值格式只能为 json 或 bridge")
        integer(request.get("timeout_ms", limits.script_timeout_ms), "script timeout", 1, limits.max_timeout_ms)
        identifier(request.get("command_id"), "command_id")
        target: JsonValue = request.get("target")
        if not ((isinstance(target, str) and target.strip()) or (isinstance(target, dict) and target)):
            raise InputError("请求必须给出明确当前目标")
        text(request.get("reason"), "reason", trim=False)
        script: JsonValue = request.get("script")
        if script is not None:
            path: Path = local_path(text(script, "script"), base)
            if path.suffix.lower() != ".cs":
                raise InputError("用户脚本文件必须为 .cs 方法体")
            SecretGuard().check_bytes(read_regular(path, limits.script_bytes))
        if request.get("correction_of") is not None:
            identifier(request["correction_of"], "correction_of")
            text(request.get("correction_reason"), "correction_reason", trim=False)
        elif request.get("correction_reason") is not None:
            raise InputError("correction_reason 必须关联 correction_of")
    if operation == "observe":
        keys_only(request, {"command_id", "observation_id", "script", "builtin", "builtin_options", "send", "scope",
                           "index", "original_text", "purpose", "target", "read_only_review", "reason", "covers_step",
                           "after_command_id", "value_format", "timeout_ms", "poll", "correction_of", "correction_reason"},
                  "observe", {"command_id", "observation_id", "purpose", "target", "read_only_review", "reason"})
        identifier(request["observation_id"], "observation_id")
        text(request["read_only_review"], "read_only_review", trim=False)
        if text(request["purpose"], "purpose") not in READ_PURPOSES:
            raise InputError("读取用途不在已知只读契约内")
        if request.get("builtin") is not None:
            if request.get("script") is not None:
                raise InputError("设备侧命名观测与手写脚本不能同时出现")
            builtin_observation(text(request["builtin"], "builtin"), object_value(request.get("builtin_options", {}), "builtin_options"))
        elif request.get("script") is None or request.get("builtin_options") is not None:
            raise InputError("observe 必须给出 script 或 builtin 之一；options 只与 builtin 同时出现")
        scope: str = text(request.get("scope", "discovery"), "observe.scope")
        if scope not in {"step", "precondition", "guard", "discovery"}:
            raise InputError("观察原索引范围非法")
        if scope == "discovery":
            if request.get("index") is not None or request.get("original_text") is not None:
                raise InputError("现场 discovery 不能冒充原步骤覆盖")
        else:
            if original is None or request.get("original_text") != original.item(scope, integer(request.get("index"), "source index")).text:
                raise InputError("只读绑定原索引/原文不匹配")
        covers: JsonValue = request.get("covers_step", False)
        if type(covers) is not bool or (covers and (scope != "step" or request["purpose"] not in {"step", "after"})):
            raise InputError("只读步骤覆盖必须显式关联原 step")
        if request.get("after_command_id") is not None:
            identifier(request["after_command_id"], "after_command_id")
        poll_condition(request.get("poll"), request.get("after_command_id"))
    elif operation == "action":
        fields: set[str] = {"command_id", "script", "builtin", "builtin_options", "send", "scope", "index", "original_text", "target",
                            "before_observation_id", "guard_comparison_ids", "target_review", "reason",
                            "value_format", "timeout_ms", "correction_of", "correction_reason"}
        keys_only(request, fields, "action", fields - {"script", "builtin", "builtin_options", "send", "value_format", "timeout_ms", "correction_of", "correction_reason"})
        if request.get("builtin") is not None:
            if request.get("script") is not None or request.get("value_format", "json") != "json":
                raise InputError("内置动作与手写脚本互斥，返回格式固定为 json")
            builtin_action_path(request)
        elif request.get("script") is None or request.get("builtin_options") is not None:
            raise InputError("action 必须给出 script 或 builtin 之一；options 只与 builtin 同时出现")
        if text(request["scope"], "action.scope") not in {"step", "precondition"}:
            raise InputError("动作只能关联原 step 或合法前置构造")
        if original is None or request["original_text"] != original.item(str(request["scope"]), integer(request["index"], "action.index")).text:
            raise InputError("动作原步骤/前置文本绑定发生变化")
        text(request["target_review"], "target_review", trim=False)
        identifier(request["before_observation_id"], "before_observation_id")
        guards: JsonValue = request["guard_comparison_ids"]
        if not isinstance(guards, list) or not guards or len(set(str(value) for value in guards)) != len(guards):
            raise InputError("动作必须关联不重复的独立守卫比较")
        for guard in guards:
            identifier(guard, "guard comparison")
    elif operation == "compare":
        binding: JsonObject = expand_rule_basis(request)
        fields = {"schema", "comparison_id", "scope", "index", "original_text", "step_indices",
                  "observation_id", "field", "operator", "basis", "before"}
        keys_only(binding, fields, "comparison", fields - {"step_indices", "before"})
        if binding["schema"] != "mono-pipeline-comparison/1" or text(binding["scope"], "comparison.scope") not in {"expected", "precondition", "guard"}:
            raise InputError("比较 schema 或原文范围不匹配")
        identifier(binding["comparison_id"], "comparison_id")
        identifier(binding["observation_id"], "comparison observation")
        scope = str(binding["scope"])
        index: int = integer(binding["index"], "comparison.index")
        if original is None or binding["original_text"] != original.item(scope, index).text:
            raise InputError("比较原索引或原预期文本不匹配；guard 取原步骤而非前置，更正必须使用新文件和新 ID")
        steps: JsonValue = binding.get("step_indices", [index] if scope == "guard" else [])
        if not isinstance(steps, list) or (scope == "expected" and not steps):
            raise InputError("每条原预期必须声明本例相关原步骤索引")
        indexes: list[int] = [integer(value, "bound step index") for value in steps]
        if len(set(indexes)) != len(indexes):
            raise InputError("原预期步骤索引重复")
        for step in indexes:
            original.item("step", step)
        check_pointer(binding["field"], "comparison.field")
        operator: str = text(binding["operator"], "comparison.operator")
        if operator not in {"eq", "ne", "gt", "ge", "lt", "le", "contains", "delta"}:
            raise InputError("未知独立比较规则")
        basis: JsonObject = object_value(binding["basis"], "comparison.basis")
        keys_only(basis, {"kind", "value", "reference_id", "field", "factor", "reviewer", "statement", "semantic_review", "original_is_text_contains"},
                  "comparison.basis", {"kind", "reviewer", "statement", "semantic_review"})
        if basis["reviewer"] != "current_agent":
            raise InputError("原自然语言到比较必须由当前 Agent 审核")
        text(basis["statement"], "basis.statement", trim=False)
        text(basis["semantic_review"], "basis.semantic_review", trim=False)
        if basis["kind"] == "literal":
            if "value" not in basis or set(basis) & {"reference_id", "field", "factor"}:
                raise InputError("literal 独立预期依据结构非法")
            expected: bool | int | float | str = scalar(basis["value"])
            if operator in {"gt", "ge", "lt", "le", "delta"} and type(expected) not in {int, float}:
                raise InputError("数值比较的独立预期必须为数值")
            if operator == "contains" and not isinstance(expected, str):
                raise InputError("contains 的独立预期必须为文本")
        elif basis["kind"] == "baseline":
            if "value" in basis or "reference_id" not in basis or "field" not in basis:
                raise InputError("配置/需求基线必须引用登记来源")
            identifier(basis["reference_id"], "baseline reference")
            check_pointer(basis["field"], "baseline.field")
            factor: JsonValue = basis.get("factor", 1)
            if type(factor) is not int or factor not in {-1, 1}:
                raise InputError("基线 factor 仅允许明确的正负方向")
        else:
            raise InputError("预期依据只能为 literal 或 baseline")
        if operator == "contains" and basis.get("original_is_text_contains") is not True:
            raise InputError("contains 必须明确审核原预期确实是文本包含")
        if operator == "delta":
            before: JsonObject = object_value(binding.get("before"), "delta.before")
            keys_only(before, {"observation_id", "field"}, "delta.before", {"observation_id", "field"})
            identifier(before["observation_id"], "before observation")
            check_pointer(before["field"], "before.field")
        elif "before" in binding:
            raise InputError("非 delta 比较不能混入 before")
    elif operation == "final":
        keys_only(request, {"status", "reason", "category", "required_permission"}, "final", {"status"})
        if text(request["status"], "final.status") not in VERDICTS:
            raise InputError("final 只允许真实四状态")
        if request["status"] == "blocked":
            if text(request.get("category"), "block category") not in {"permission", "environment", "critical_precondition", "user_stop"}:
                raise InputError("blocked 需要明确来源")
            if request.get("category") == "permission":
                if text(request.get("required_permission"), "required_permission") not in PERMISSIONS:
                    raise InputError("权限阻塞必须引用已知权限")
        elif request["status"] == "test_inconclusive" and text(request.get("category"), "inconclusive category") not in {"insufficient_observation", "not_constructible"}:
            raise InputError("不确定只能来自真实尝试，必须声明合法 category，禁止 not_attempted")
        if request["status"] in {"blocked", "test_inconclusive"}:
            text(request.get("reason"), "non-passed.reason", trim=False)
    elif operation == "chain-start":
        parse_chain_source(request, limits)
    elif operation == "chain-end":
        keys_only(request, set(), "chain-end")
    elif operation == "start-case":
        keys_only(request, {"case_id", "group_id"}, "start-case", {"case_id"})
        if original is None or text(request["case_id"], "case_id") != original.case_id:
            raise InputError("开始用例必须绑定完整原例")
        text(request.get("group_id", "ungrouped"), "group_id")
    elif operation == "note":
        keys_only(request, {"case_id", "category", "message", "related_seq"}, "note", {"category", "message", "related_seq"})
        if text(request["category"], "note.category") not in {"gap_explanation", "overrun_reason", "source_lookup", "blockage", "rollback_risk"}:
            raise InputError("note 类别非法")
        text(request["message"], "note.message", trim=False)
        integer(request["related_seq"], "related_seq")
    elif operation == "baseline":
        keys_only(request, {"reference_id", "kind", "path", "sha256", "review"}, "baseline", {"reference_id", "kind", "path", "sha256", "review"})
        identifier(request["reference_id"], "reference_id")
        if text(request["kind"], "baseline.kind") not in {"configuration", "requirements"}:
            raise InputError("基线类别不明")
        expected_hash: str = hash_value(request["sha256"], "baseline.sha256")
        baseline_path: Path = local_path(text(request["path"], "baseline.path"), base)
        baseline_raw: bytes = read_regular(baseline_path, limits.input_bytes)
        if digest(baseline_raw) != expected_hash:
            raise InputError("独立基线草稿摘要与实际原字节不匹配")
        SecretGuard().check(strict_json(baseline_raw, limits.input_bytes, limits, bom=True))
        text(request["review"], "baseline.review", trim=False)
    elif operation in {"attribute", "reference"}:
        fields = ({"case_id", "classification", "issue_id", "description", "root_cause", "verification", "comparison_ids", "observation_ids"}
                  if operation == "attribute" else {"case_id", "description", "target", "observation_ids", "comparison_ids", "source_lookup"})
        required: set[str] = fields - ({"issue_id", "root_cause"} if operation == "attribute" else {"source_lookup"})
        keys_only(request, fields, operation, required)
        text(request["case_id"], operation + ".case_id")
        text(request["description"], operation + ".description", trim=False)
        for key in ("observation_ids", "comparison_ids"):
            values: JsonValue = request[key]
            if not isinstance(values, list):
                raise InputError(operation + " 必须列实际观察/比较 ID")
            for value in values:
                identifier(value, operation + "." + key)
        if operation == "attribute":
            text(request["verification"], "verification", trim=False)
            if text(request["classification"], "classification") not in {"product_confirmed", "unattributed_failure", "locator_error", "environment_blocked", "condition_not_constructible", "tool_error"}:
                raise InputError("归因类别不在固定口径内")
    elif operation == "collect-evidence":
        keys_only(request, {"observation_id", "field", "privacy_review"}, "collect-evidence", {"observation_id", "field", "privacy_review"})
        identifier(request["observation_id"], "artifact observation")
        check_pointer(request["field"], "artifact.field")
        review: JsonObject = object_value(request["privacy_review"], "privacy_review")
        keys_only(review, {"reviewer", "statement"}, "privacy_review", {"reviewer", "statement"})
        if review["reviewer"] != "current_agent":
            raise InputError("附件必须由当前 Agent 做敏感审查")
        text(review["statement"], "privacy_review.statement", trim=False)


# 功能：批量执行前，对每条不确定/阻塞收口的理由做一次「理由-事实」自检并返回可打印清单；参数 parsed 为静态预检后的用例计划。
# 边界：只打印事实供当前 Agent 复核，不改变任何判定；批级 0 动作告警用于暴露「可执行却全部收口」的误判。
def suite_reason_selfcheck(parsed: list[tuple[str, str, list[tuple[str, JsonObject]]]]) -> list[str]:
    lines: list[str] = []
    batch_observed: bool = any(operation == "observe" for _, _, steps in parsed for operation, _ in steps)
    batch_actions: int = sum(1 for _, _, steps in parsed for operation, _ in steps if operation == "action")
    batch_notes: int = sum(1 for _, _, steps in parsed for operation, _ in steps if operation == "note")
    batch_statuses: dict[str, int] = {}
    for _case_id, _group, steps in parsed:
        status: JsonValue = steps[-1][1].get("status")
        batch_statuses[str(status)] = batch_statuses.get(str(status), 0) + 1
    if batch_actions == 0:
        unexplained: list[str] = [case_id for case_id, _group, steps in parsed
                                  if not any(operation == "note" for operation, _ in steps)]
        lines.append(
            "[自检] 本批 0 个 action 步骤；纯只读例可以无动作，含交互原步骤须核对未执行原因；不绕过真实前置。"
            f"本批 note={batch_notes}，statuses={batch_statuses}，未留 note 的用例={unexplained}"
        )
    for case_id, _group, steps in parsed:
        final_request: JsonObject = steps[-1][1]
        status = final_request.get("status")
        if status not in {"test_inconclusive", "blocked"}:
            continue
        case_observed: bool = any(operation == "observe" for operation, _ in steps)
        case_actions: int = sum(1 for operation, _ in steps if operation == "action")
        reason: str = str(final_request.get("reason", "")).strip().replace("\n", " ")
        snippet: str = reason[:60] + ("…" if len(reason) > 60 else "")
        fact: str = "本例已有 observe" if case_observed else ("他例 observe 不能替代本例事实" if batch_observed else "本批尚无任何 observe，理由无本轮事实支撑")
        lines.append(
            f"[自检] {case_id} status={status} category={final_request.get('category')} "
            f"fact={fact} actions={case_actions} reason=\"{snippet}\""
        )
    return lines


# 功能：汇总原格式计划的覆盖事实；参数parsed已静态校验，不猜字段语义、不预判现场状态、不读取Player。
def planning_summary(parsed: list[tuple[str, str, list[tuple[str, JsonObject]]]],
                     cases: CaseInput | None = None) -> JsonObject:
    rows: list[JsonValue] = []
    statuses: JsonObject = {}
    terminal: list[JsonValue] = []
    action_cases: list[JsonValue] = []
    for case_id, _, steps in parsed:
        status: str = str(steps[-1][1]["status"])
        statuses[status] = int(cast(int, statuses.get(status, 0))) + 1
        actions: list[JsonObject] = [request for operation, request in steps if operation == "action"]
        action_step_indices: list[int] = sorted({integer(request["index"], "step index") for request in actions
                                                  if request.get("scope") == "step"})
        original: OriginalCase | None = cases.case(case_id) if cases is not None else None
        action_required_indices: list[int] = ([] if original is None else
            [item.index for item in original.steps if step_requires_action(item.text)])
        missing_action_indices: list[int] = sorted(set(action_required_indices) - set(action_step_indices))
        expected: list[int] = sorted({integer(request["index"], "expected index") for operation, request in steps
                                     if operation == "compare" and request.get("scope") == "expected"})
        if actions:
            action_cases.append(case_id)
        if not actions and not expected:
            terminal.append(case_id)
        bindings: list[JsonValue] = []
        for operation, request in steps:
            if operation == "compare" and request.get("scope") == "precondition":
                binding: JsonObject = expand_rule_basis(request)
                basis: JsonObject = object_value(binding["basis"], "plan basis")
                bindings.append({"index": binding["index"], "original_text": binding["original_text"],
                    "field": binding["field"], "operator": binding["operator"],
                    **({"value": basis["value"]} if basis["kind"] == "literal" else {"basis": basis})})
        rows.append({"case_id": case_id, "requested_status": status,
            "action_count": len(actions),
            "action_step_indices": action_step_indices,
            "action_required_step_indices": action_required_indices,
            "missing_required_action_step_indices": missing_action_indices,
            "readonly_step_indices": sorted({integer(request["index"], "step index") for operation, request in steps
                if operation == "observe" and request.get("covers_step") is True}),
            "expected_indices": expected, "precondition_bindings": bindings})
    return {"status_counts": statuses, "action_case_ids": action_cases, "terminal_only_case_ids": terminal,
            "cases": rows, "semantic_equivalence_proven": False}


# 功能：生成共用成员读取体；参数 name/options 为旧单字段或组件多路径观察，header 提供节点路径函数。
def builtin_member_observation(name: str, options: JsonObject, header: str) -> bytes:
    root: str = cast(str, options.get("root", ""))
    single: bool = name == "logic_field"
    type_name: str = text(options.get("logic_type" if single else "component_type"), "builtin member type")
    paths: JsonValue = [options.get("field")] if single else options.get("members")
    if not single and not root.strip():
        raise InputError("member_probe 必须给出 root，限定真实组件范围")
    if not isinstance(paths, list) or not 1 <= len(paths) <= BUILTIN_MAX_MEMBERS:
        raise InputError("builtin.members 必须为 1..32 条成员路径")
    for path in paths:
        if (not isinstance(path, str) or len(path) > 512 or
                not 1 <= len(path.split(".")) <= BUILTIN_MAX_MEMBER_DEPTH or
                any(not part.isidentifier() for part in path.split("."))):
            raise InputError("成员路径只允许点分隔字段/属性名，至多8层，不接受调用或索引表达式")
    if len(set(cast(list[str], paths))) != len(paths):
        raise InputError("builtin.members 不得重复")
    limit: int = integer(options.get("max_nodes", 1500), "builtin.max_nodes", 1, BUILTIN_MAX_NODES)
    # 只执行明确点名的 getter；中间对象仅用于沿路径读取，返回前投影为基础 JSON 值。
    reader: str = r'''
System.Reflection.BindingFlags __flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.DeclaredOnly;
// Read a named field or property, preserving missing/read errors independently.
System.Func<object,string,System.Collections.Generic.Dictionary<string,object>> __readMember = delegate(object __owner, string __name) {
    System.Collections.Generic.Dictionary<string,object> __r = new System.Collections.Generic.Dictionary<string,object> {
        {"found", false}, {"readable", false}, {"member_kind", null}, {"value_type", null}, {"value", null}, {"error", null} };
    if (__owner == null || (__owner is UnityEngine.Object && (UnityEngine.Object)__owner == null)) { __r["error"] = "member_owner_missing"; return __r; }
    try {
        for (System.Type __type = __owner.GetType(); __type != null; __type = __type.BaseType) {
            System.Reflection.MemberInfo[] __members = __type.GetMember(__name, System.Reflection.MemberTypes.Field | System.Reflection.MemberTypes.Property, __flags);
            if (__members.Length == 0) { continue; }
            __r["found"] = true;
            if (__members.Length != 1) { __r["error"] = "member_ambiguous"; return __r; }
            System.Reflection.FieldInfo __f = __members[0] as System.Reflection.FieldInfo;
            System.Reflection.PropertyInfo __p = __members[0] as System.Reflection.PropertyInfo;
            __r["member_kind"] = __f != null ? "field" : "property";
            __r["value_type"] = __f != null ? __f.FieldType.FullName : (__p == null ? null : __p.PropertyType.FullName);
            if (__f == null && (__p == null || __p.GetIndexParameters().Length != 0 || __p.GetGetMethod(true) == null)) {
                __r["error"] = "member_not_readable"; return __r;
            }
            object __value = __f != null ? __f.GetValue(__owner) : __p.GetValue(__owner, null);
            __r["readable"] = true; __r["value"] = __value;
            if (__value != null) { __r["value_type"] = __value.GetType().FullName; }
            return __r;
        }
        __r["error"] = "member_missing";
    } catch (System.Exception) { __r["error"] = "member_read_failed"; }
    return __r;
};
// Traverse only the requested path, then reject objects and non-finite numbers.
System.Func<object,string,System.Collections.Generic.Dictionary<string,object>> __probeMember = delegate(object __owner, string __memberPath) {
    System.Collections.Generic.Dictionary<string,object> __r = null;
    foreach (string __part in __memberPath.Split('.')) {
        __r = __readMember(__owner, __part);
        if (!(bool)__r["readable"]) { __r["failed_segment"] = __part; break; }
        __owner = __r["value"];
    }
    if (__r == null) { throw new System.InvalidOperationException("empty_member_path"); }
    object __v = __r["value"];
    if ((bool)__r["readable"] && __v != null) {
        System.Type __type = __v.GetType();
        System.TypeCode __code = System.Type.GetTypeCode(__type);
        if (__type.IsEnum || __v is char) { __r["value"] = __v.ToString(); }
        else if (__code == System.TypeCode.Object || __code == System.TypeCode.DateTime || __code == System.TypeCode.DBNull) {
            __r["readable"] = false; __r["value"] = null; __r["error"] = "unsupported_value_type";
        } else if ((__v is double && (double.IsNaN((double)__v) || double.IsInfinity((double)__v))) ||
                   (__v is float && (float.IsNaN((float)__v) || float.IsInfinity((float)__v)))) {
            __r["readable"] = false; __r["value"] = null; __r["error"] = "non_finite_value";
        }
    }
    return __r;
};
'''
    type_match: str = (
        "System.Func<object,bool> __matches = delegate(object __candidate) {\n"
        "    if (__candidate == null) { return false; }\n"
        "    for (System.Type __type = __candidate.GetType(); __type != null; __type = __type.BaseType) {\n"
        "        if (__type.FullName == " + json.dumps(type_name) + " || __type.Name == " + json.dumps(type_name) + ") { return true; }\n"
        + ("        break;\n" if single else "") +
        "    } return false;\n};\n"
    )
    adapter: str = r'''
    if (!__matches(__candidate)) {
        __candidate = __readMember(__component, "UILogicInst")["value"];
        if (!__matches(__candidate)) {
            object __adapter = __readMember(__component, "m_MonoInvocationAdapter")["value"];
            __candidate = __readMember(__adapter, "m_Instance")["value"];
        }
    }
''' if single else ""
    scan: str = (
        "System.Collections.Generic.List<object> __instances = new System.Collections.Generic.List<object>();\n"
        "System.Collections.Generic.List<UnityEngine.Component> __components = new System.Collections.Generic.List<UnityEngine.Component>();\n"
        "string __root = " + json.dumps(root) + ";\n"
        "foreach (UnityEngine.Component __component in UnityEngine.Resources.FindObjectsOfTypeAll<UnityEngine.Component>()) {\n"
        "    if (__component == null || __component.gameObject == null || !__component.gameObject.scene.IsValid()) { continue; }\n"
        "    string __p = __path(__component.transform);\n"
        "    if (__root.Length != 0 && __p != __root && !__p.StartsWith(__root + \"/\", System.StringComparison.Ordinal)) { continue; }\n"
        "    object __candidate = __component;\n" + adapter +
        "    if (!__matches(__candidate)) { continue; }\n"
        + ("    if (__instances.Exists(delegate(object __prior) { return object.ReferenceEquals(__prior, __candidate); })) { continue; }\n" if single else "") +
        "    __instances.Add(__candidate); __components.Add(__component);\n"
        "}\n"
    )
    if single:
        tail: str = (
            "object __inst = __instances.Count == 1 ? __instances[0] : null;\n"
            "System.Collections.Generic.Dictionary<string,object> __result = __probeMember(__inst, " + json.dumps(paths[0]) + ");\n"
            "if (__inst == null) { __result[\"error\"] = __instances.Count == 0 ? \"instance_missing\" : \"instance_ambiguous\"; }\n"
            "__result[\"logic_type\"] = " + json.dumps(type_name) + "; __result[\"field\"] = " + json.dumps(paths[0]) + ";\n"
            "__result[\"instance_count\"] = __instances.Count;\n"
            "return __result;\n"
        )
    else:
        tail = (
            "string[] __paths = new string[] { " + ", ".join(json.dumps(path) for path in paths) + " };\n"
            "for (int __i = 0; __i < __instances.Count && __i < " + str(limit) + "; __i++) {\n"
            "    UnityEngine.Component __component = __components[__i];\n"
            "    System.Collections.Generic.Dictionary<string,object> __values = new System.Collections.Generic.Dictionary<string,object>();\n"
            "    foreach (string __memberPath in __paths) { __values[__memberPath] = __probeMember(__instances[__i], __memberPath); }\n"
            "    __rows.Add(new System.Collections.Generic.Dictionary<string,object> {\n"
            "        {\"path\", __path(__component.transform)}, {\"active\", __component.gameObject.activeInHierarchy},\n"
            "        {\"instance_id\", __component.GetInstanceID()}, {\"component_type\", __component.GetType().FullName}, {\"members\", __values} });\n"
            "}\n"
            "return new System.Collections.Generic.Dictionary<string,object> {\n"
            "    {\"op\", \"member_probe\"}, {\"instance_count\", __instances.Count}, {\"count\", __rows.Count},\n"
            "    {\"truncated\", __instances.Count > __rows.Count}, {\"nodes\", __rows} };\n"
        )
    return (header + reader + type_match + scan + tail).encode("utf-8")


# 功能：生成设备侧命名观测脚本；参数 name 为已登记 op 名、options 为其参数，返回 C# 方法体字节。
# 边界：只返回业务事实（层级/激活/文本/图片/开关/可交互/私有字段），绝不返回 success/assertion/passed/verdict。
def builtin_observation(name: str, options: JsonObject) -> bytes:
    if name not in BUILTIN_OBSERVATIONS:
        raise InputError("未知设备侧观测 op；只允许 chain/subtree/buttons/logic_field/member_probe")
    allowed: set[str] = ({"root", "component_type", "members", "max_nodes"} if name == "member_probe" else
        {"depth", "max_nodes", "root", "name_contains", "logic_type", "field", "names_only"})
    keys_only(options, allowed, "builtin_options")
    names_only: JsonValue = options.get("names_only", False)
    if type(names_only) is not bool or (names_only and name not in {"chain", "subtree"}):
        raise InputError("names_only 仅为 chain/subtree 的布尔选项")
    # 深度从真实场景根（如 GameEntry）算起；本项目 UI 实例位于 GameEntry/Builtin/UI/AdapterArea/Canvas0/<UI>，
    # 即第 6 层，因此默认 6 层以覆盖「不显式给 depth 也能拿到界面」的常见用法。
    depth: int = integer(options.get("depth", 6), "builtin.depth", 1, BUILTIN_MAX_DEPTH)
    limit: int = integer(options.get("max_nodes", 1500), "builtin.max_nodes", 1, BUILTIN_MAX_NODES)
    for key in ("root", "name_contains", "logic_type", "field", "component_type"):
        if key in options and not isinstance(options[key], str):
            raise InputError("builtin." + key + " 必须为文本")
    root: str = cast(str, options.get("root", ""))
    node_name: str = cast(str, options.get("name_contains", ""))
    header: str = (
        "// 设备侧命名观测；只返回业务事实，不返回任何成功/断言标记。\n"
        "System.Collections.Generic.List<object> __rows = new System.Collections.Generic.List<object>();\n"
        "System.Func<UnityEngine.Transform,string> __path = null;\n"
        "__path = delegate(UnityEngine.Transform t) {\n"
        "    if (t == null) { return \"\"; }\n"
        "    string p = __path(t.parent);\n"
        "    return p.Length == 0 ? t.name : p + \"/\" + t.name;\n"
        "};\n"
    )
    if name in {"logic_field", "member_probe"}:
        return builtin_member_observation(name, options, header)
    # 场景遍历刻意不依赖 SceneManager 强类型：只用 FindObjectsOfTypeAll 取全部 Transform。
    # 必须无条件排除非场景对象（预制体资源、未实例化模板），否则同名资源根会被当成场景根，
    # 导致同一 UI 取到未激活的那一份、并产生重复 path。DontDestroyOnLoad 场景 scene.IsValid() 仍为 true，不受影响。
    scan: str = (
        "System.Collections.Generic.List<UnityEngine.GameObject> __roots = new System.Collections.Generic.List<UnityEngine.GameObject>();\n"
        "System.Collections.Generic.HashSet<int> __seenRoot = new System.Collections.Generic.HashSet<int>();\n"
        "foreach (UnityEngine.Transform __t in UnityEngine.Resources.FindObjectsOfTypeAll<UnityEngine.Transform>()) {\n"
        "    if (__t == null) { continue; }\n"
        "    UnityEngine.GameObject __go = __t.gameObject;\n"
        "    if (__go.transform.parent != null) { continue; }\n"
        "    if (!__go.scene.IsValid()) { continue; }\n"
        "    if (!__seenRoot.Add(__go.GetInstanceID())) { continue; }\n"
        "    __roots.Add(__go);\n"
        "}\n"
    )
    # 先按标准 UGUI 强类型取 text/interactable/isOn；未命中再按组件名 + 公共属性反射取，
    # 使项目自定义控件（GameText/GameButton/GameToggle）在 Roslyn 无其强类型引用时仍能读到实际值。
    probe: str = (
        "System.Func<UnityEngine.Transform,string,string,object> __prop = delegate(UnityEngine.Transform __t, string __type, string __name) {\n"
        "    if (__t == null) { return null; }\n"
        "    foreach (UnityEngine.Component __c in __t.GetComponents<UnityEngine.Component>()) {\n"
        "        if (__c == null || __c.GetType().Name != __type) { continue; }\n"
        "        System.Reflection.PropertyInfo __pr = __c.GetType().GetProperty(__name, System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public);\n"
        "        if (__pr == null || !__pr.CanRead || __pr.GetIndexParameters().Length != 0) { continue; }\n"
        "        try { return __pr.GetValue(__c, null); } catch (System.Exception) { return null; }\n"
        "    }\n"
        "    return null;\n"
        "};\n"
    )
    walk: str = (
        "System.Action<UnityEngine.Transform,int> __walk = null;\n"
        "__walk = delegate(UnityEngine.Transform __t, int __d) {\n"
        "    if (__t == null || __d > " + str(depth) + " || __rows.Count >= " + str(limit) + ") { return; }\n"
        "    UnityEngine.GameObject __go = __t.gameObject;\n"
        "    string __p = __path(__t);\n"
        "    System.Collections.Generic.Dictionary<string, object> __row = new System.Collections.Generic.Dictionary<string, object> {\n"
        "        {\"path\", __p}, {\"name\", __go.name}, {\"active\", __go.activeInHierarchy} };\n"
        "    UnityEngine.UI.Text __txt = __t.GetComponent<UnityEngine.UI.Text>();\n"
        "    if (__txt != null) { __row[\"text\"] = __txt.text; }\n"
        "    else { object __tv = __prop(__t, \"GameText\", \"text\"); if (__tv != null) { __row[\"text\"] = __tv; } }\n"
        "    object __textColor = __txt == null ? __prop(__t, \"GameText\", \"color\") : (object)__txt.color;\n"
        "    if (__textColor is UnityEngine.Color) {\n"
        "        __row[\"text_color_rgb\"] = UnityEngine.ColorUtility.ToHtmlStringRGB((UnityEngine.Color)__textColor).ToLowerInvariant();\n"
        "        __row[\"text_color_rgba\"] = UnityEngine.ColorUtility.ToHtmlStringRGBA((UnityEngine.Color)__textColor).ToLowerInvariant();\n"
        "    }\n"
        "    UnityEngine.UI.Image __image = __t.GetComponent<UnityEngine.UI.Image>();\n"
        "    object __rawSprite = __image == null ? __prop(__t, \"GameImage\", \"sprite\") : (object)__image.sprite;\n"
        "    UnityEngine.Sprite __sprite = __rawSprite as UnityEngine.Sprite;\n"
        "    if (__sprite != null) { __row[\"sprite_name\"] = __sprite.name; }\n"
        "    else if (__image != null) { __row[\"sprite_name\"] = null; }\n"
        "    object __imageColor = __image == null ? __prop(__t, \"GameImage\", \"color\") : (object)__image.color;\n"
        "    if (__imageColor is UnityEngine.Color) {\n"
        "        __row[\"image_color_rgb\"] = UnityEngine.ColorUtility.ToHtmlStringRGB((UnityEngine.Color)__imageColor).ToLowerInvariant();\n"
        "        __row[\"image_color_rgba\"] = UnityEngine.ColorUtility.ToHtmlStringRGBA((UnityEngine.Color)__imageColor).ToLowerInvariant();\n"
        "    }\n"
        "    UnityEngine.UI.Button __btn = __t.GetComponent<UnityEngine.UI.Button>();\n"
        "    if (__btn != null) { __row[\"interactable\"] = __btn.interactable; }\n"
        "    else { object __bv = __prop(__t, \"GameButton\", \"interactable\"); if (__bv != null) { __row[\"interactable\"] = __bv; } }\n"
        "    UnityEngine.UI.Toggle __tog = __t.GetComponent<UnityEngine.UI.Toggle>();\n"
        "    if (__tog != null) { __row[\"isOn\"] = __tog.isOn; }\n"
        "    else { object __gv = __prop(__t, \"GameToggle\", \"isOn\"); if (__gv != null) { __row[\"isOn\"] = __gv; } }\n"
        "    __rows.Add(__row);\n"
        "    for (int __i = 0; __i < __t.childCount; __i++) { __walk(__t.GetChild(__i), __d + 1); }\n"
        "};\n"
    )
    if names_only:
        walk = (
            "System.Action<UnityEngine.Transform,int> __walk = null;\n"
            "__walk = delegate(UnityEngine.Transform __t, int __d) {\n"
            "    if (__t == null || __d > " + str(depth) + " || __rows.Count >= " + str(limit) + ") { return; }\n"
            "    __rows.Add(new System.Collections.Generic.Dictionary<string, object> {\n"
            "        {\"path\", __path(__t)}, {\"name\", __t.gameObject.name}, {\"active\", __t.gameObject.activeInHierarchy} });\n"
            "    for (int __i = 0; __i < __t.childCount; __i++) { __walk(__t.GetChild(__i), __d + 1); }\n"
            "};\n"
        )
    if name == "chain":
        # 常量条件 if(false) 会触发 CS0162；仅在确有 root 过滤时才生成判断。
        driver: str = "foreach (UnityEngine.GameObject __r in __roots) { __walk(__r.transform, 0); }\n" if not root else (
            "foreach (UnityEngine.GameObject __r in __roots) {\n"
            "    foreach (UnityEngine.Transform __t in __r.GetComponentsInChildren<UnityEngine.Transform>(true)) {\n"
            "        if (__path(__t) == " + json.dumps(root) + ") { __walk(__t, 0); }\n"
            "    }\n"
            "}\n"
        )
    elif name == "subtree":
        if not root:
            raise InputError("subtree 必须给出 root 路径")
        driver = (
            "UnityEngine.GameObject __start = null;\n"
            "foreach (UnityEngine.GameObject __r in __roots) {\n"
            "    UnityEngine.Transform[] __all = __r.GetComponentsInChildren<UnityEngine.Transform>(true);\n"
            "    foreach (UnityEngine.Transform __t in __all) { if (__path(__t) == " + json.dumps(root) + ") { __start = __t.gameObject; break; } }\n"
            "    if (__start != null) { break; }\n"
            "}\n"
            "if (__start != null) { __walk(__start.transform, 0); }\n"
        )
    else:  # buttons
        filter_text: str = ("if (" + json.dumps(node_name) + " != \"\" && __p.IndexOf(" + json.dumps(node_name) + ", System.StringComparison.OrdinalIgnoreCase) < 0) { continue; }\n            ") if node_name else ""
        root_filter: str = ("if (__p != " + json.dumps(root) + " && !__p.StartsWith(" + json.dumps(root + "/") + ", System.StringComparison.Ordinal)) { continue; }\n") if root else ""
        driver = (
            "foreach (UnityEngine.GameObject __r in __roots) {\n"
            "    foreach (UnityEngine.Transform __t in __r.GetComponentsInChildren<UnityEngine.Transform>(true)) {\n"
            "        if (__rows.Count >= " + str(limit) + ") { break; }\n"
            "        string __p = __path(__t);\n"
            "        " + root_filter +
            "        " + filter_text +
            "System.Collections.Generic.List<UnityEngine.Component> __custom = new System.Collections.Generic.List<UnityEngine.Component>();\n"
            "        System.Collections.Generic.List<UnityEngine.Component> __native = new System.Collections.Generic.List<UnityEngine.Component>();\n"
            "        foreach (UnityEngine.Component __c in __t.GetComponents<UnityEngine.Component>()) {\n"
            "            if (__c == null) { continue; }\n"
            "            if (__c.GetType().Name == \"GameButton\") { __custom.Add(__c); }\n"
            "            else if (__c is UnityEngine.UI.Button) { __native.Add(__c); }\n"
            "        }\n"
            "        System.Collections.Generic.List<UnityEngine.Component> __candidates = __custom.Count > 0 ? __custom : __native;\n"
            "        if (__candidates.Count == 0) { continue; }\n"
            "        UnityEngine.Component __button = __candidates.Count == 1 ? __candidates[0] : null;\n"
            "        UnityEngine.UI.Button __b = __button as UnityEngine.UI.Button;\n"
            "        object __interactable = __button == null ? null : (__b == null ? __prop(__t, \"GameButton\", \"interactable\") : (object)__b.interactable);\n"
            "        UnityEngine.Behaviour __behaviour = __button as UnityEngine.Behaviour;\n"
            "        object __effective = null; string __clickMethod = null;\n"
            "        if (__button != null) {\n"
            "            System.Reflection.MethodInfo __can = __button.GetType().GetMethod(\"IsInteractable\", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public, null, System.Type.EmptyTypes, null);\n"
            "            if (__can != null && __can.ReturnType == typeof(bool)) { try { __effective = __can.Invoke(__button, null); } catch (System.Exception) { } }\n"
            "            if (__b != null && __b.onClick != null) { __clickMethod = \"onClick.Invoke\"; }\n"
            "            else {\n"
            "                System.Reflection.MethodInfo __click = __button.GetType().GetMethod(\"InvokeOnClickListener\", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public, null, System.Type.EmptyTypes, null);\n"
            "                if (__click != null && __click.ReturnType == typeof(void)) { __clickMethod = \"InvokeOnClickListener\"; }\n"
            "            }\n"
            "        }\n"
            "        UnityEngine.UI.Text __txt = __t.GetComponentInChildren<UnityEngine.UI.Text>(true);\n"
            "        object __text = __txt == null ? null : (object)__txt.text;\n"
            "        if (__text == null) { foreach (UnityEngine.Transform __child in __t.GetComponentsInChildren<UnityEngine.Transform>(true)) { __text = __prop(__child, \"GameText\", \"text\"); if (__text != null) { break; } } }\n"
            "        __rows.Add(new System.Collections.Generic.Dictionary<string, object> {\n"
            "            {\"path\", __p}, {\"active\", __t.gameObject.activeInHierarchy},\n"
            "            {\"interactable\", __interactable}, {\"effective_interactable\", __effective}, {\"text\", __text},\n"
            "            {\"button_count\", __candidates.Count}, {\"node_instance_id\", __t.gameObject.GetInstanceID()},\n"
            "            {\"instance_id\", __button == null ? null : (object)__button.GetInstanceID()},\n"
            "            {\"component_type\", __button == null ? null : __button.GetType().FullName},\n"
            "            {\"enabled\", __behaviour == null ? null : (object)__behaviour.isActiveAndEnabled}, {\"click_method\", __clickMethod} });\n"
            "    }\n"
            "}\n"
        )
    tail: str = (
        "return new System.Collections.Generic.Dictionary<string, object> {\n"
        "    {\"op\", " + json.dumps(name) + "}, {\"count\", __rows.Count},\n"
        "    {\"truncated\", __rows.Count >= " + str(limit) + "}, {\"nodes\", __rows} };\n"
    )
    # probe 必须整体排在 walk 之前：C# 局部变量先声明后使用，否则 __prop 在 __walk 委托内不可见（CS0103）。
    return (header + scan + ("" if names_only else probe) + ("" if name == "buttons" else walk) + driver + tail).encode("utf-8")


# 功能：校验固定点击入口的公开参数；参数 request 只携带最新 buttons 中的真实完整节点路径。
def builtin_action_path(request: JsonObject) -> str:
    if request.get("builtin") != "click_button":
        raise InputError("未知内置动作；当前仅支持 click_button")
    options: JsonObject = object_value(request.get("builtin_options"), "builtin_options")
    keys_only(options, {"path"}, "click_button options", {"path"})
    path: str = text(options["path"], "click_button.path")
    if path.startswith("/") or path.endswith("/") or "//" in path:
        raise InputError("点击路径必须使用本例 buttons 返回的完整节点路径")
    return path


# 功能：取得当前路径唯一且可交互的按钮原值；参数before为宿主观察，path为其完整节点路径。
def builtin_button_row(path: str, before: JsonObject) -> JsonObject:
    actual: JsonObject = object_value(before.get("value"), "button observation")
    nodes: JsonValue = actual.get("nodes")
    if actual.get("op") != "buttons" or actual.get("truncated") is not False or not isinstance(nodes, list) or type(actual.get("count")) is not int or actual["count"] != len(nodes):
        raise InputError("内置点击要求完整、未截断的 builtin:buttons 观测")
    rows: list[JsonObject] = [object_value(node, "button node") for node in nodes]
    selected: list[JsonObject] = [row for row in rows if row.get("path") == path]
    if len(selected) != 1:
        raise InputError("点击目标在最新 buttons 中缺失或路径不唯一")
    row: JsonObject = selected[0]
    for key in ("instance_id", "node_instance_id"):
        if type(row.get(key)) is not int or not -2147483648 <= cast(int, row[key]) <= 2147483647 or row[key] == 0:
            raise InputError("点击要求真实非零 Int32 实例标识")
    if type(row.get("button_count")) is not int or row["button_count"] != 1 or any(row.get(key) is not True for key in ("active", "enabled", "interactable", "effective_interactable")):
        raise InputError("点击目标存在组件歧义、未激活或不可交互")
    text(row.get("component_type"), "button component type")
    if row.get("click_method") not in {"InvokeOnClickListener", "onClick.Invoke"}:
        raise InputError("点击目标缺少已验证的公开点击接口")
    return row


# 功能：从可信 before 派生并再次核验按钮实例，调用一次公开方法；参数 options 不接受用户手填实例或类型。
def builtin_button_click(options: JsonObject, before: JsonObject) -> bytes:
    path: str = builtin_action_path({"builtin": "click_button", "builtin_options": options})
    row: JsonObject = builtin_button_row(path, before)
    current: str = builtin_observation("buttons", {"root": path, "max_nodes": BUILTIN_MAX_NODES}).decode("utf-8")
    body: str = (
        "// mono-pipeline-builtin-click/1; Codex: one public invocation after identity checks.\n"
        "System.Func<object> __mpft_click_read = delegate() {\n" + current + "\n};\n"
        "System.Collections.Generic.Dictionary<string,object> __mpft_buttons = (System.Collections.Generic.Dictionary<string,object>)__mpft_click_read();\n"
        "System.Collections.Generic.List<object> __mpft_rows = (System.Collections.Generic.List<object>)__mpft_buttons[\"nodes\"];\n"
        "System.Collections.Generic.Dictionary<string,object> __mpft_selected = null; int __mpft_matches = 0;\n"
        "foreach (object entry in __mpft_rows) {\n"
        "    System.Collections.Generic.Dictionary<string,object> row = (System.Collections.Generic.Dictionary<string,object>)entry;\n"
        "    if (System.Object.Equals(row[\"path\"], " + json.dumps(path) + ")) { __mpft_selected = row; __mpft_matches++; }\n"
        "}\n"
        "if (!System.Object.Equals(__mpft_buttons[\"truncated\"], false) || __mpft_matches != 1 || __mpft_selected == null) { throw new System.InvalidOperationException(\"button_selection_changed\"); }\n"
    )
    for key in ("path", "instance_id", "node_instance_id", "component_type", "button_count", "active", "enabled", "interactable", "effective_interactable", "click_method"):
        body += "if (!System.Object.Equals(__mpft_selected[" + json.dumps(key) + "], " + json.dumps(row[key]) + ")) { throw new System.InvalidOperationException(\"button_identity_or_state_changed\"); }\n"
    body += (
        "UnityEngine.Component __mpft_button = null; int __mpft_componentCount = 0;\n"
        "foreach (UnityEngine.Component component in UnityEngine.Resources.FindObjectsOfTypeAll<UnityEngine.Component>()) {\n"
        "    if (component == null || !component.gameObject.scene.IsValid() || component.GetInstanceID() != " + str(row["instance_id"]) + ") { continue; }\n"
        "    if (component.GetType().FullName != " + json.dumps(str(row["component_type"])) + ") { continue; }\n"
        "    __mpft_button = component; __mpft_componentCount++;\n"
        "}\n"
        "if (__mpft_button == null || __mpft_componentCount != 1) { throw new System.InvalidOperationException(\"button_instance_changed\"); }\n"
    )
    if row["click_method"] == "InvokeOnClickListener":
        body += (
            "System.Reflection.MethodInfo __mpft_click = __mpft_button.GetType().GetMethod(\"InvokeOnClickListener\", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public, null, System.Type.EmptyTypes, null);\n"
            "if (__mpft_click == null || __mpft_click.ReturnType != typeof(void)) { throw new System.InvalidOperationException(\"button_method_changed\"); }\n"
            "__mpft_click.Invoke(__mpft_button, null);\n"
        )
    else:
        body += (
            "UnityEngine.UI.Button __mpft_native = __mpft_button as UnityEngine.UI.Button;\n"
            "if (__mpft_native == null || __mpft_native.onClick == null) { throw new System.InvalidOperationException(\"button_method_changed\"); }\n"
            "__mpft_native.onClick.Invoke();\n"
        )
    body += 'return new System.Collections.Generic.Dictionary<string,object> { {"method_called", true}, {"path", ' + json.dumps(path) + '} };\n'
    return body.encode("utf-8")


@dataclass
class CaseState:
    """只从本轮 journal 重建本例关联，最终结果不可覆盖。"""

    started: JsonObject
    group_id: str
    observations: dict[str, JsonObject] = field(default_factory=dict)
    comparisons: dict[str, JsonObject] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    covered_steps: set[int] = field(default_factory=set)
    final: JsonObject | None = None
    failed_comparisons: list[str] = field(default_factory=list)
    # 用例级隔离：严格只读片段失败或身份可信的返回契约错误，不牵连本轮其他用例。
    frozen: bool = False
    freeze_reason: str = ""
    # 显式完成条件的真实轮询记录：物理序号、关联动作、确认帧是否满足；旧记录默认没有完成门槛。
    completion_checks: list[tuple[int, str, bool]] = field(default_factory=list)

    # 功能：查询当前或某事件之前的待完成动作；参数 before_seq 供审计按当时事实回算。
    def completion_pending(self, before_seq: int | None = None) -> str | None:
        for sequence, action_id, matched in reversed(self.completion_checks):
            if before_seq is None or sequence < before_seq:
                return None if matched else action_id
        return None


# 功能：从实际样本与声明 ID 的确认帧回算完成条件；参数 start_seq 限定本次轮询，不采用脚本自述结论。
def completion_confirmed(item: CaseState, condition: JsonObject, poll_id: str, start_seq: int) -> bool:
    if not item.actions:
        return False
    observations: list[JsonObject] = [value for value in item.observations.values()
        if integer(value["record_seq"], "completion observation seq") > start_seq]
    confirmations: list[JsonObject] = [value for value in observations if value["command_id"] == poll_id]
    if len(confirmations) != 1 or observations[-1] is not confirmations[0]:
        return False
    stable: int = 0
    last_frame: int = -1
    try:
        for observation in observations:
            if observation.get("valid") is not True or observation.get("after_command_id") != item.actions[-1]:
                stable = 0
                continue
            matches, ignored = compare_values(str(condition["operator"]),
                field_value(observation.get("value"), str(condition["field"])), condition["value"])
            if observation is confirmations[0]:
                return matches and stable >= integer(condition.get("stable_samples", 1), "stable_samples", 1, 8)
            frame: int = integer(observation["frame"], "completion frame", 0)
            if frame > last_frame:
                stable = stable + 1 if matches else 0
                last_frame = frame
    except InputError:
        return False
    return False


@dataclass
class RunState:
    """持久动作 ID 和未知阶段；不存在自动解冻或恢复接口。"""

    cases: dict[str, CaseState] = field(default_factory=dict)
    commands: dict[str, JsonObject] = field(default_factory=dict)
    results: dict[str, JsonObject] = field(default_factory=dict)
    references: dict[str, JsonObject] = field(default_factory=dict)
    current: str | None = None
    attached: bool = False
    frozen: bool = False
    freeze_reason: str = ""
    closed: JsonObject | None = None
    timing: JsonObject | None = None
    report: JsonObject | None = None
    report_intent: bool = False
    integrity_interrupted: bool = False
    # 共享准备独立于原用例；其观察/动作仍由同一 journal 重建，但没有业务 final。
    chain_original: OriginalCase | None = None
    chain_closed: JsonObject | None = None


# 功能：从已经验链的本轮事件重建状态；参数 cases 保持完整原用例基准。
def replay(records: list[JsonObject], cases: CaseInput, root: Path,
           snapshot_cache: dict[tuple[str, str], JsonObject] | None = None) -> RunState:
    state: RunState = RunState()
    cache: dict[tuple[str, str], JsonObject] = snapshot_cache if snapshot_cache is not None else {}
    for record in records:
        event: JsonValue = record["event"]
        data: JsonObject = record_data(record)
        case_id: JsonValue = record["case_id"]
        if state.timing is not None and event in BUSINESS_EVENTS:
            raise IntegrityError("业务事件出现在计时闭合之后")
        if event == "session_attached":
            if state.closed is not None or state.frozen:
                raise IntegrityError("冻结/关闭后出现附加事件")
            state.attached = True
        elif event == "session_frozen":
            state.frozen = True
            state.freeze_reason = text(data.get("reason"), "freeze.reason", trim=False)
        elif event == "case_frozen":
            # 用例级冻结：只标记该例，本轮其他用例不受影响。
            if not isinstance(case_id, str) or case_id not in state.cases:
                raise IntegrityError("用例级冻结不属于已开始用例")
            state.cases[case_id].frozen = True
            state.cases[case_id].freeze_reason = text(data.get("reason"), "case freeze reason", trim=False)
        elif event == "source_integrity_interrupted":
            if not state.frozen or state.closed is not None or state.integrity_interrupted:
                raise IntegrityError("来源中断必须属于尚未关闭的唯一冻结会话")
            if data.get("formal_report_eligible") is not False or data.get("snapshot_only") is not True:
                raise IntegrityError("来源失效不能冒充正式审计或恢复执行")
            state.integrity_interrupted = True
        elif event == "chain_started":
            if case_id != CONTROL_CASE or state.cases or state.current is not None or state.closed is not None or not state.attached or state.frozen:
                raise IntegrityError("共享链路必须唯一建立于附加后、首条原用例前")
            if data.get("source_kind") != "input":
                raise IntegrityError("共享链路来源不能冒充业务原用例")
            state.chain_original = parse_chain_source(object_value(data.get("source"), "chain source"), Limits())
            state.current = CONTROL_CASE
            state.cases[CONTROL_CASE] = CaseState(record, text(data.get("group_id"), "chain group"))
        elif event == "chain_closed":
            item_chain: CaseState | None = state.cases.get(CONTROL_CASE)
            if case_id != CONTROL_CASE or state.current != CONTROL_CASE or state.chain_original is None or item_chain is None or state.chain_closed is not None:
                raise IntegrityError("共享链路收口归属或唯一性非法")
            coverage_chain: JsonObject = case_coverage(state.chain_original, item_chain)
            if data.get("ready") is not True or state.frozen or item_chain.frozen or coverage_chain["all_matched"] is not True or data.get("coverage") != coverage_chain:
                raise IntegrityError("共享准备未独立验证或未知阶段不能声明链路就绪")
            if state.chain_original.raw.get("capability_gate") is not None:
                gate_error: str | None = chain_action_gate_error(state.chain_original, item_chain, state.commands)
                if gate_error is not None:
                    raise IntegrityError(gate_error)
            state.chain_closed = record
            state.current = None
        elif event == "case_started":
            if not isinstance(case_id, str) or case_id in state.cases or state.current is not None or state.closed is not None:
                raise IntegrityError("本例开始归属重复或已有活动例")
            cases.case(case_id)
            state.current = case_id
            state.cases[case_id] = CaseState(record, text(data.get("group_id"), "group_id"))
        elif event == "intent":
            command_id: str = identifier(data.get("command_id"), "command_id")
            if command_id in state.commands or state.closed is not None or state.frozen:
                raise IntegrityError("动作/读取 ID 重复或冻结后出现 intent")
            if data.get("mode") != "probe" and (case_id != state.current or case_id not in state.cases):
                raise IntegrityError("intent 不属于当前本例")
            state.commands[command_id] = record
        elif event == "command_result":
            command_id = identifier(data.get("command_id"), "command_id")
            if command_id not in state.commands or command_id in state.results:
                raise IntegrityError("回执缺少唯一 intent 或重复")
            intent: JsonObject = state.commands[command_id]
            if intent["case_id"] != case_id:
                raise IntegrityError("回执/intent 跨例")
            state.results[command_id] = record
            receipt: JsonObject = object_value(data.get("receipt"), "receipt")
            if receipt.get("state") == "unknown":
                # 脚本自身缺陷（phase=script_failed）只冻结该用例；身份/协议/传输失真仍冻结整轮。
                if receipt.get("phase") == "script_failed" and isinstance(case_id, str) and record_data(intent).get("mode") == "read":
                    state.cases[case_id].frozen = True
                    state.cases[case_id].freeze_reason = text(receipt.get("diagnostic"), "case freeze diagnostic", trim=False)
                else:
                    state.frozen = True
                    state.freeze_reason = text(receipt.get("diagnostic"), "unknown diagnostic", trim=False)
            elif (receipt.get("state") == "succeeded" and isinstance(case_id, str)
                  and record_data(intent).get("mode") == "read"
                  and str(data.get("observation_error", "")).startswith("return_value_contract:")):
                state.cases[case_id].frozen = True
                state.cases[case_id].freeze_reason = str(data["observation_error"])
            if isinstance(case_id, str):
                item: CaseState = state.cases[case_id]
                request: JsonObject = record_data(intent)
                if request.get("mode") == "action" and receipt.get("state") == "succeeded":
                    item.actions.append(command_id)
                    if request.get("scope") == "step":
                        item.covered_steps.add(integer(request.get("index"), "step index"))
                observation_ref: JsonValue = data.get("observation_ref")
                if observation_ref is not None:
                    reference: JsonObject = object_value(observation_ref, "observation ref")
                    # 内存按证据摘要缓存观察快照；摘要是内容哈希，命中即字节等价，不降低任何校验严格度。
                    cache_key: tuple[str, str] = (str(reference["path"]), str(reference["sha256"]))
                    cached: JsonObject | None = cache.get(cache_key)
                    if cached is not None:
                        snapshot: JsonObject = cached
                    else:
                        snapshot = object_value(strict_json(read_regular(root / str(reference["path"]), Limits().evidence_bytes), Limits().evidence_bytes), "observation")
                        cache[cache_key] = snapshot
                    observation_id: str = identifier(snapshot.get("observation_id"), "observation_id")
                    if observation_id in item.observations or snapshot.get("case_id") != case_id or snapshot.get("command_id") != command_id or data.get("observation_id") != observation_id:
                        raise IntegrityError("独立观察 ID 重复、跨例或与回执不符")
                    item.observations[observation_id] = {**snapshot, "record_seq": record["seq"], "evidence": reference}
                    if request.get("covers_step") is True and snapshot.get("valid") is True:
                        item.covered_steps.add(integer(request.get("index"), "read step index"))
        elif event == "poll_closed":
            start_seq: int = integer(data.get("start_seq"), "poll start seq", 1, integer(record["seq"], "poll close seq") - 1)
            start: JsonObject = records[start_seq - 1]
            condition: JsonObject = object_value(record_data(start).get("condition"), "poll condition")
            if start["event"] != "poll_started" or start["case_id"] != case_id or record_data(start).get("poll_id") != data.get("poll_id"):
                raise IntegrityError("轮询闭合未关联本例实际开始记录")
            if condition.get("require_match") is True:
                completion_item: CaseState | None = state.cases.get(str(case_id))
                if completion_item is None or completion_item.final is not None or not completion_item.actions or type(data.get("matched")) is not bool:
                    raise IntegrityError("业务完成条件缺少本例动作或真实轮询结论")
                action_id: str = completion_item.actions[-1]
                confirmed: bool = completion_confirmed(completion_item, condition, str(data["poll_id"]), start_seq)
                if data["matched"] is not confirmed:
                    raise IntegrityError("业务完成记录与实际稳定样本及确认帧不一致")
                if data["matched"] is True:
                    confirmation: JsonObject | None = completion_item.observations.get(str(data.get("last_observation_id")))
                    if confirmation is None or confirmation.get("valid") is not True or confirmation.get("after_command_id") != action_id or confirmation.get("command_id") != data["poll_id"]:
                        raise IntegrityError("业务完成缺少本次动作后的有效确认观察")
                completion_item.completion_checks.append((integer(record["seq"], "completion seq"), action_id, data["matched"] is True))
        elif event == "comparison":
            if case_id not in state.cases or case_id != state.current:
                raise IntegrityError("比较不属于活动用例")
            comparison_id: str = identifier(data.get("comparison_id"), "comparison_id")
            item = state.cases[str(case_id)]
            if comparison_id in item.comparisons:
                raise IntegrityError("原预期比较 ID 被覆盖")
            item.comparisons[comparison_id] = data
            binding: JsonObject = object_value(data.get("binding"), "comparison binding")
            if data.get("valid") is True and data.get("matched") is False and binding.get("scope") == "expected":
                item.failed_comparisons.append(comparison_id)
        elif event == "case_final":
            if case_id == CONTROL_CASE:
                raise IntegrityError("共享准备不能产生业务用例 final")
            if case_id not in state.cases or case_id != state.current or state.cases[str(case_id)].final is not None:
                raise IntegrityError("每例 final 必须唯一且实时")
            if data.get("status") not in VERDICTS:
                raise IntegrityError("final 四状态非法")
            state.cases[str(case_id)].final = record
            state.current = None
        elif event == "baseline_registered":
            reference_id: str = identifier(data.get("reference_id"), "reference_id")
            if reference_id in state.references:
                raise IntegrityError("已登记独立基线被覆盖")
            state.references[reference_id] = data
        elif event == "session_closed":
            if state.closed is not None:
                raise IntegrityError("会话关闭重复")
            state.closed = record
            state.attached = False
        elif event == "timing_closed":
            if state.timing is not None or state.closed is None:
                raise IntegrityError("本轮计时必须在关闭后唯一闭合")
            state.timing = record
        elif event == "report_intent":
            if state.report_intent:
                raise IntegrityError("正式报告 intent 重复")
            state.report_intent = True
        elif event == "report_rendered":
            if state.report is not None or not state.report_intent:
                raise IntegrityError("正式报告必须唯一并有 intent")
            state.report = record
    pending: list[str] = [command_id for command_id in state.commands if command_id not in state.results]
    if pending:
        state.frozen = True
        state.freeze_reason = "发现发送前 intent 但无可靠结果；阶段未知，禁止恢复或重放"
    return state


# 功能：共用原索引缺口计算；参数集合仅表示已覆盖或拟覆盖索引，不作自然语言语义判断。
def coverage_gaps(original: OriginalCase, steps: set[int], expected: set[int], preconditions: set[int]) -> JsonObject:
    return {"missing_steps": [item.index for item in original.steps if item.index not in steps],
            "missing_expected": [item.index for item in original.expected if item.index not in expected],
            "missing_preconditions": [item.index for item in original.preconditions if item.index not in preconditions]}


# 功能：计算每例原步骤/预期/前置缺口及有效反例；参数 state 不能替代原输入。
def case_coverage(original: OriginalCase, state: CaseState) -> JsonObject:
    expected: dict[int, JsonObject] = {}
    preconditions: set[int] = set()
    for comparison in state.comparisons.values():
        binding: JsonObject = object_value(comparison["binding"], "binding")
        if comparison.get("valid") is True:
            index: int = integer(binding.get("index"), "source index")
            if binding.get("scope") == "expected":
                expected[index] = comparison
            elif binding.get("scope") == "precondition" and comparison.get("matched") is True:
                preconditions.add(index)
    gaps: JsonObject = coverage_gaps(original, state.covered_steps, set(expected), preconditions)
    failed: list[str] = list(state.failed_comparisons)
    complete: bool = not any(gaps.values())
    return {"covered_steps": sorted(state.covered_steps), **gaps,
            "compared_expected": sorted(expected), "failed_comparisons": failed,
            "complete": complete, "all_matched": complete and not failed and state.completion_pending() is None
            and all(value.get("matched") is True for value in expected.values())}


# 功能：返回各请求 scope 对应的完整原文和显式索引；参数 original 不重编号，guard 取原步骤而非原前置。
def binding_sources(original: OriginalCase) -> JsonObject:
    collections: dict[str, tuple[SourceItem, ...]] = {"precondition": original.preconditions,
        "step": original.steps, "guard": original.steps, "expected": original.expected}
    return {scope: [{"scope": scope, "index": item.index, "original_text": item.text} for item in items]
            for scope, items in collections.items()}


# 功能：离线初始化完整原输入及明确配置；参数输出根由调用方指定，不连接或探测 Player。
def initialize(cases_path: Path, target_path: Path, output_root: Path,
               provenance_path: Path | None = None, parent_root: Path | None = None,
               workflow_timing: Path | None = None, workflow_parent_id: str | None = None,
               workflow_child_id: str | None = None, run_prefix: str = "run") -> Path:
    defaults: Limits = Limits()
    target_raw: bytes = read_regular(target_path, defaults.input_bytes)
    target: TargetConfig = parse_target(strict_json(target_raw, defaults.input_bytes, bom=True), target_path.parent)
    cases_raw: bytes = read_regular(cases_path, target.limits.input_bytes)
    cases: CaseInput = parse_cases(cases_raw, target.limits)
    source_paths: list[tuple[Path, bytes]] = [(cases_path, cases_raw), (target_path, target_raw)]
    for path in (target.package_manifest, target.license_path):
        source_paths.append((path, read_regular(path, target.limits.source_bytes)))
    if provenance_path is not None:
        raw: bytes = read_regular(provenance_path, target.limits.input_bytes)
        document: JsonValue = strict_json(raw, target.limits.input_bytes, target.limits, bom=True)
        for source in parse_provenance(document, cases, provenance_path.parent, target.limits):
            path: Path = Path(str(source["path"]))
            source_paths.append((path, read_regular(path, target.limits.source_bytes)))
        source_paths.append((provenance_path, raw))
    workflow: JsonObject | None = None
    supplied: tuple[object, ...] = (workflow_timing, workflow_parent_id, workflow_child_id)
    if any(value is not None for value in supplied):
        if workflow_timing is None or workflow_parent_id is None or workflow_child_id is None or parent_root is not None:
            raise InputError("统一父交接必须三项齐全，且不得另建包内父上下文")
        workflow = bind_workflow(workflow_timing, workflow_parent_id, workflow_child_id, target.limits)
    parent: JsonObject | None = None
    if parent_root is not None:
        with Journal(parent_root) as context:
            if not context.records or context.records[0]["event"] != "parent_init" or any(record["event"] in {"parent_closed", "report_intent"} for record in context.records):
                raise InputError("父上下文必须为包内 writer 创建且未关闭/渲染")
            parent = {"root": str(parent_root.absolute()), "invocation_id": context.run_id,
                      "init_hash": context.records[0]["hash"], "report_owner": "parent"}
    identifier(run_prefix, "run prefix")
    run_id: str = new_id(run_prefix)
    identifier(run_id, "run id")
    root: Path = local_path(str(output_root), Path.cwd(), missing_leaf=True)
    run_root: Path = root / run_id
    budget: JsonObject = run_path_budget(run_root)
    if budget["supported"] is not True:
        raise InputError("Windows 证据路径预算超限：最长 " + str(budget["longest_evidence_units"]) +
                         "、上限 " + str(budget["windows_limit_units"]) + " UTF-16 单元；输出根最多 " +
                         str(budget["maximum_output_root_units"]) +
                         " 单元。先用 output-check 选择更短安全根；尚未创建本轮或接触 Player")
    root.mkdir(parents=True, exist_ok=True)
    journal: Journal = Journal.create(run_root, target.limits)
    with journal:
        sources: list[JsonObject] = []
        seen: set[str] = set()
        for path, content in source_paths:
            if str(path.absolute()).casefold() not in seen:
                seen.add(str(path.absolute()).casefold())
                sources.append(journal.origin(path.absolute(), content))
        case_origin: JsonObject = sources[0]
        index: JsonObject = journal.store("index", canonical(case_index(cases)), {"kind": "input_index", "sha256": cases.raw_sha256})
        journal.append("run_init", {"case_input": case_origin, "case_index": index, "sources": sources,
                                    "target": target.to_json(), "parent": parent, "workflow": workflow,
                                    "report_owner": "coordinator" if workflow else ("parent" if parent else "self"),
                                    "case_ids": [case.case_id for case in cases.cases], "mode": "mono_exploration",
                                    "upload": "not_executed"}, run_id=run_id)
        journal.append("cli_result", {"operation": "init", "call_id": new_id("call"), "ok": True,
                                      "result": {"run_id": run_id, "root": str(run_root), "case_count": len(cases.cases), "attached": False}})
    if parent_root is not None:
        with Journal(parent_root) as context:
            context.append("child_registered", {"run_id": run_id, "root": str(run_root), "init_hash": journal.records[0]["hash"]})
    return run_root


class Session:
    """每次 CLI 重建的本轮宿主；通过 journal 保持现场逐条执行，而不是导出静态计划。"""

    # 功能：保存本轮目录与测试调用层依赖；参数构造不连接/操作目标。
    def __init__(self, root: Path, hooks: IdentityHooks | None = None,
                 factory: Callable[[int, str, Limits], Transport] = LocalHttp) -> None:
        self.journal: Journal = Journal(root)
        self.hooks: IdentityHooks = hooks if hooks is not None else IdentityHooks()
        self.factory: Callable[[int, str, Limits], Transport] = factory
        self.cases: CaseInput | None = None
        self.target: TargetConfig | None = None
        self.state: RunState = RunState()
        self._request_origin: JsonObject | None = None
        self._request_base: Path = Path.cwd()
        self._source_integrity_valid: bool = True
        # 同一命令内复用唯一正常连接；跨 CLI 进程仍重新建连与重验身份。
        self._pipeline: Pipeline | None = None
        # 同一命令内按证据摘要复用观察快照；摘要变化即重新严格读取。
        self._snapshot_cache: dict[tuple[str, str], JsonObject] = {}

    # 功能：锁定本轮、核验输入并重建现场状态；参数无，不自动附加或恢复。
    def __enter__(self) -> Session:
        self.journal.__enter__()
        try:
            if not self.journal.records or self.journal.records[0]["event"] != "run_init":
                raise InputError("指定目录不是主动测试本轮会话")
            initial: JsonObject = record_data(self.journal.records[0])
            self.target = parse_target(initial.get("target"), self.journal.root)
            self.journal.limits = self.target.limits
            origin: JsonObject = object_value(initial.get("case_input"), "case_input")
            snapshot: JsonObject = object_value(origin.get("snapshot"), "case_input.snapshot")
            self.cases = parse_cases(self.journal.verify_ref(snapshot), self.target.limits)
            self._refresh()
            pending: bool = any(command_id not in self.state.results for command_id in self.state.commands)
            if pending and not any(record["event"] == "session_frozen" for record in self.journal.records):
                self._freeze("发现发送前 intent 但无可靠结果；不能恢复或重放", "lost_receipt", None)
        except BaseException:
            self.journal.__exit__(None, None, None)
            raise
        return self

    # 功能：释放本次唯一 writer；参数异常对象不记录原文。
    def __exit__(self, exception_type: object, exception: object, traceback: object) -> None:
        self.journal.__exit__(exception_type, exception, traceback)

    # 功能：重新读取物理状态，不能由临时内存覆盖 final；参数无。
    def _refresh(self) -> None:
        if self.cases is None:
            raise IntegrityError("完整原用例尚未加载")
        self.state = replay(self.journal.records, self.cases, self.journal.root, self._snapshot_cache)


    # 功能：核验私有证据、外部来源与实际父绑定；参数 local_terminal 仅允许外部失效后的状态/中断，不绕过快照。
    def verify_sources(self, local_terminal: bool = False) -> bool:
        initial: JsonObject = record_data(self.journal.records[0])
        sources: JsonValue = initial.get("sources")
        if not isinstance(sources, list):
            raise IntegrityError("原来源登记缺失")
        origins: list[JsonObject] = [object_value(value, "source") for value in sources]
        for record in self.journal.records:
            data: JsonObject = record_data(record)
            for key in ("request_origin", "origin"):
                if data.get(key) is not None:
                    origins.append(object_value(data[key], "binding origin"))
            self.journal.verify_references(data)
        valid: bool = True
        if local_terminal:
            for origin in origins:
                try:
                    self.journal.verify_origin(origin)
                except (InputError, IntegrityError):
                    valid = False
        else:
            self._verify_origins(origins)
        if initial.get("workflow") is not None:
            workflow: JsonObject = verify_workflow(object_value(initial["workflow"], "workflow binding"), self.journal.limits,
                                                   self.journal.records[0]["time_utc"],
                                                   self.state.timing["time_utc"] if self.state.timing is not None else None)
            if self.state.closed is None and object_value(workflow["child"], "workflow child").get("skill_end_time") is not None:
                raise IntegrityError("原 Mono 子计时已结束，禁止继续未收口的宿主会话")
        if self.state.integrity_interrupted:
            if not local_terminal:
                raise IntegrityError("本轮已按来源失效中断；即使外部文件恢复，也不得恢复执行、正式审计或报告")
            valid = False
        return valid

    # 功能：并行核验全部已登记外部来源；参数 origins 来自真实 journal 记录，任一失败统一按完整性问题拒绝，错误语义与串行一致。
    def _verify_origins(self, origins: list[JsonObject]) -> None:
        if len(origins) < 4:
            for origin in origins:
                try:
                    self.journal.verify_origin(origin)
                except (InputError, IntegrityError):
                    raise IntegrityError("原来源或已登记绑定失效；拒绝继续，仅允许本地状态及明确中断关闭") from None
            return
        workers: int = min(8, max(2, os.cpu_count() or 2))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending: list[Future[None]] = [pool.submit(self.journal.verify_origin, origin) for origin in origins]
            for future in pending:
                try:
                    future.result()
                except (InputError, IntegrityError):
                    raise IntegrityError("原来源或已登记绑定失效；拒绝继续，仅允许本地状态及明确中断关闭") from None

    # 功能：永久冻结整轮；参数 phase/command_id 保存未知阶段，不表示代码已终止。
    def _freeze(self, reason: str, phase: str, command_id: str | None) -> None:
        if not any(record["event"] == "session_frozen" for record in self.journal.records):
            self.journal.append("session_frozen", {"reason": reason, "phase": phase,
                                                   "command_id": command_id, "execution_terminated": False})
        self._refresh()

    # 功能：只冻结当前用例；参数 reason/command_id 记录脚本自身缺陷现场，不牵连本轮其他用例。
    def _freeze_case(self, case_id: str, reason: str, phase: str, command_id: str | None) -> None:
        already: bool = any(record["event"] == "case_frozen" and record["case_id"] == case_id
                            for record in self.journal.records)
        if not already:
            self.journal.append("case_frozen", {"reason": reason, "phase": phase,
                                                "command_id": command_id, "execution_terminated": False}, case_id)
        self._refresh()

    # 功能：检查活跃/冻结门禁；参数 player=True 时整轮未知或本例已用例级冻结都禁止再接触 Player。
    def _active(self, player: bool = False) -> None:
        if self.state.closed is not None:
            raise InputError("本轮已关闭，不能继续业务操作")
        if player and self.state.frozen:
            raise FrozenSession("整轮已冻结；可能仍在执行，禁止附加/观察/动作/重放")
        if player and self.state.current is not None:
            current: CaseState | None = self.state.cases.get(self.state.current)
            if current is not None and current.frozen:
                raise FrozenSession("本例已因脚本自身缺陷冻结；只允许收口本例或开始新例，禁止继续接触 Player")

    # 功能：取得指定原文索引来源；参数 case_id 仅在已登记共享准备时允许控制来源，不扩充原业务全集。
    def original_case(self, case_id: str) -> OriginalCase:
        if case_id == CONTROL_CASE and self.state.chain_original is not None:
            return self.state.chain_original
        if self.cases is None:
            raise IntegrityError("完整原用例尚未加载")
        return self.cases.case(case_id)

    # 功能：取得本例及原用例或已登记共享准备；参数无，收口后禁止继续执行当前上下文。
    def _current(self) -> tuple[str, OriginalCase, CaseState]:
        if self.cases is None or self.state.current is None:
            raise InputError("必须先开始当前原用例")
        case_id: str = self.state.current
        return case_id, self.original_case(case_id), self.state.cases[case_id]

    # 功能：将每次请求/真实结果写入同一 journal；参数 origin_path 为不可静默改写的 CLI 请求来源。
    def invoke(self, operation: str, parameters: JsonObject, origin_path: Path | None = None) -> JsonObject:
        if operation not in OPERATIONS:
            raise InputError("未知 CLI 会话操作")
        call_id: str = new_id("call")
        self.journal.append("cli_begin", {"operation": operation, "call_id": call_id})
        self._request_origin = None
        self._request_base = origin_path.parent if origin_path is not None else Path.cwd()
        try:
            self._source_integrity_valid = self.verify_sources(local_terminal=operation in {"status", "close"})
            if not self._source_integrity_valid and self.state.closed is None:
                self._freeze("已登记外部来源失效；只允许本地状态及明确中断收口", "integrity", None)
            SecretGuard().check(parameters)
            # 在来源登记前拒绝结构/当前关联错误；已成功登记的来源仍不可变，未知动作仍整轮冻结。
            self.check_request(operation, parameters, self._request_base)
            if origin_path is not None:
                raw: bytes = read_regular(origin_path, self.journal.limits.input_bytes)
                parsed: JsonObject = object_value(strict_json(raw, self.journal.limits.input_bytes, bom=True), "CLI request")
                if canonical(parsed) != canonical(parameters):
                    raise IntegrityError("CLI 请求来源字节在登记前变化")
                self._request_origin = self.journal.origin(origin_path, raw, "binding", self.state.current or CONTROL_CASE)
                self.journal.append("request_registered", {"operation": operation, "call_id": call_id,
                                                           "request_origin": self._request_origin}, self.state.current)
            result: JsonObject = self._handler(operation)(parameters)
            self.journal.append("cli_result", {"operation": operation, "call_id": call_id, "ok": True, "result": result})
            self._refresh()
            return result
        except HostError as exc:
            if isinstance(exc, IntegrityError) and self.state.closed is None:
                self._freeze("来源/绑定/证据完整性异常；原文已排除，停止后续动作", "integrity", None)
            self.journal.append("cli_result", {"operation": operation, "call_id": call_id, "ok": False,
                                              "error_kind": type(exc).__name__, "message": str(exc)})
            self._refresh()
            raise
        except (Exception, KeyboardInterrupt):
            pending: list[str] = [command_id for command_id in self.state.commands if command_id not in self.state.results]
            for command_id in pending:
                intent: JsonObject = self.state.commands[command_id]
                unknown: EvalReceipt = EvalReceipt("unknown", "host_after_intent", None, "宿主意外异常/中断，执行阶段未知；原异常未回显")
                self.journal.append("command_result", {"command_id": command_id, "receipt": unknown.to_json(),
                                                       "frame": None, "observation_id": record_data(intent).get("observation_id"),
                                                       "observation_ref": None, "observation_valid": False, "observation_error": unknown.diagnostic,
                                                       "not_executed": False, "effective_timeout_ms": 0}, cast(str | None, intent["case_id"]))
            self._freeze("宿主非结构化异常/中断；不自动恢复或重放", "host_failure", pending[-1] if pending else None)
            self.journal.append("cli_result", {"operation": operation, "call_id": call_id, "ok": False,
                                               "error_kind": "HostFailure", "message": "宿主异常已排除；本轮已冻结"})
            self._refresh()
            raise FrozenSession("宿主异常/中断后冻结；原文已排除") from None

    # 功能：返回已登记会话操作的实现；参数 operation 必须属于固定契约，不做动态分发。
    def _handler(self, operation: str) -> Callable[[JsonObject], JsonObject]:
        if operation not in OPERATIONS:
            raise InputError("未知 CLI 会话操作")
        return {
            "attach": self._attach, "status": self._status, "chain-start": self._chain_start, "chain-end": self._chain_end,
            "start-case": self._start,
            "observe": self._observe, "action": self._action, "compare": self._compare,
            "final": self._final, "attribute": self._attribute, "baseline": self._baseline,
            "reference": self._reference, "collect-evidence": self._collect_evidence,
            "note": self._note, "close": self._close if self._source_integrity_valid else self._close_integrity,
            "audit": self._audit, "report": self._report,
        }[operation]

    # 功能：只读核验单次请求的结构和当前本例关联；参数 base 是草稿目录，不写 journal、不建连或消耗 ID。
    def check_request(self, operation: str, request: JsonObject, base: Path | None = None) -> JsonObject:
        if operation not in OPERATIONS:
            raise InputError("未知 CLI 会话操作")
        previous: Path = self._request_base
        self._request_base = base if base is not None else previous
        try:
            original: OriginalCase | None = None
            if self.cases is not None:
                case_id: JsonValue = request.get("case_id") if operation == "start-case" else self.state.current
                if isinstance(case_id, str):
                    original = self.cases.case(case_id) if operation == "start-case" else self.original_case(case_id)
            limits: Limits = self.target.limits if self.target is not None else self.journal.limits
            check_request_contract(operation, request, original, limits, self._request_base)
            if operation == "chain-start":
                self._chain_start(request, dry_run=True)
            elif operation == "chain-end":
                self._chain_end(request, dry_run=True)
            elif operation == "observe":
                self._read_request(request)
            elif operation == "action":
                self._check_action(request)
            elif operation == "compare":
                case_id_checked, source, item = self._current()
                self._binding(request, source, item)
            elif operation == "final":
                if self.state.current == CONTROL_CASE:
                    raise InputError("共享准备必须使用 chain-end，不产生或借用业务 final")
                self._final(request, dry_run=True)
            return {"operation": operation, "player_contacted": False, "journal_written": False, "source_registered": False}
        finally:
            self._request_base = previous

    # 功能：核验后以唯一文件名独占发布请求；参数 directory 是交付根/证据根外的请求目录，草稿不会成为登记来源。
    def publish_request(self, operation: str, request: JsonObject, directory: Path, base: Path | None = None) -> Path:
        source_base: Path = base if base is not None else self._request_base
        payload: JsonObject = dict(request)
        for key in (("script",) if operation in {"observe", "action"} else ("path",) if operation == "baseline" else ()):
            if payload.get(key) is not None:
                payload[key] = str(local_path(text(payload[key], key), source_base))
        self.check_request(operation, payload, source_base)
        output: Path = directory.absolute()
        if output.is_relative_to(Path(__file__).absolute().parent.parent) or output.is_relative_to(self.journal.root):
            raise InputError("请求目录不能污染严格交付根或私有证据根")
        reject_links(output, missing_leaf=True)
        output.mkdir(parents=True, exist_ok=True)
        path: Path = output / (new_id("request") + ".json")
        write_new(path, canonical(payload) + b"\n")
        return path

    # 功能：发布不可变请求后调用正常单步宿主；参数与 publish_request 相同，不重试、不吞业务反例或未知阶段。
    def submit(self, operation: str, request: JsonObject, directory: Path, base: Path | None = None) -> JsonObject:
        path: Path = self.publish_request(operation, request, directory, base)
        payload: JsonObject = object_value(strict_json(read_regular(path, self.journal.limits.input_bytes), self.journal.limits.input_bytes), "published request")
        return self.invoke(operation, payload, path)

    # 功能：静态预检一个用例的计划体；参数 body/seen_commands 共用，defaults 补机械字段，references 保存本批先前基线，不接触 Player。
    def _parse_case_body(self, body: JsonObject, seen_commands: set[str], step_total: list[int],
                         defaults: JsonObject | None = None,
                         references: set[str] | None = None) -> tuple[str, str, list[tuple[str, JsonObject]]]:
        keys_only(body, SUITE_CASE_KEYS, "case plan", {"case_id", "steps"})
        case_id: str = text(body["case_id"], "plan.case_id")
        group: str = text(body.get("group_id", "ungrouped"), "plan.group_id")
        raw_steps: JsonValue = body["steps"]
        if not isinstance(raw_steps, list) or not raw_steps or len(raw_steps) > PLAN_STEP_LIMIT:
            raise InputError("用例计划步骤数非法")
        if self.cases is None:
            raise IntegrityError("完整原用例尚未加载")
        original: OriginalCase = self.cases.case(case_id)
        if self.state.closed is not None:
            raise InputError("本轮已关闭，不能提交新的用例执行计划")
        if self.state.frozen:
            raise FrozenSession("本轮已冻结，不能提交新的用例执行计划")
        if self.state.current is not None:
            raise InputError("本轮已有活动用例；先用 status 确认并收口，不能提交新的 start-case 计划")
        if case_id in self.state.cases:
            raise InputError("计划包含本轮已开始或已收口的用例，不能重开或重放")
        shared: JsonObject = defaults if defaults is not None else {}
        steps: list[tuple[str, JsonObject]] = []
        for raw in raw_steps:
            item: JsonObject = object_value(raw, "plan step")
            keys_only(item, PLAN_STEP_KEYS, "plan step", PLAN_STEP_KEYS)
            operation: str = text(item["operation"], "plan step.operation")
            if operation not in PLAN_OPERATIONS:
                raise InputError("用例计划步骤操作不在允许范围")
            # 计划级 defaults 只补缺失的机械字段，原文/索引/字段/操作符/独立预期仍须逐条写。
            request: JsonObject = apply_plan_defaults(operation, object_value(item["request"], "plan step.request"), shared)
            SecretGuard().check(request)
            limits: Limits = self.target.limits if self.target is not None else self.journal.limits
            check_request_contract(operation, request, original, limits, self._request_base)
            command_id: JsonValue = request.get("command_id")
            if command_id is not None:
                name: str = identifier(command_id, "plan command_id")
                if name in seen_commands or name in self.state.commands:
                    raise InputError("计划内命令 ID 重复；同一 ID 绝不重放")
                seen_commands.add(name)
            # 只做与后续处理完全一致的原索引/原文核对，不预判任何运行期状态。
            scope: JsonValue = request.get("scope")
            if operation in {"observe", "compare", "action"} and isinstance(scope, str) and scope in {"step", "precondition", "guard", "expected"} and request.get("index") is not None:
                index: int = integer(request["index"], "plan source index")
                if request.get("original_text") != original.item(scope, index).text:
                    raise InputError("计划步骤原索引或原文与完整原用例不一致")
            steps.append((operation, request))
        step_total[0] += len(steps)
        if step_total[0] > SUITE_STEP_LIMIT:
            raise InputError("计划总步骤数超出上限")
        if steps[0][0] != "start-case" or str(steps[0][1].get("case_id")) != case_id:
            raise InputError("每个用例计划必须以本例 start-case 开头且 case_id 一致")
        finals: list[int] = [position for position, (operation, _) in enumerate(steps) if operation == "final"]
        if finals != [len(steps) - 1]:
            raise InputError("每个用例计划必须恰好以唯一 final 收口")
        # 跨步骤引用静态预检：把「引用不存在/未来的观测、比较、动作」这类构造错误提前到接触 Player 之前。
        try:
            self._check_plan_references(steps, set(self.state.references) if references is None else references)
            self._check_plan_final(original, steps)
        except InputError as exc:
            raise InputError("用例 " + case_id + "：" + str(exc)) from None
        return case_id, group, steps

    # 功能：前移 final 可静态确定的条件；参数 original/steps 保留原全集，仅检查声明而不预判现场匹配。
    def _check_plan_final(self, original: OriginalCase, steps: list[tuple[str, JsonObject]]) -> None:
        final_request: JsonObject = steps[-1][1]
        if final_request.get("status") == "failed" and not any(
            operation == "compare" and request.get("scope") == "expected" for operation, request in steps
        ):
            raise InputError("拟失败用例必须声明本例原预期比较")
        if final_request.get("status") == "blocked":
            category: JsonValue = final_request.get("category")
            if category == "critical_precondition" and not any(
                operation == "compare" and request.get("scope") == "precondition" for operation, request in steps
            ):
                raise InputError("关键前置阻塞必须声明本例原前置比较")
            if category == "environment" and not any(record["event"] == "environment_blocked" for record in self.journal.records):
                raise InputError("环境阻塞缺少本轮真实环境阻断记录")
            if category == "permission" and (self.target is None or final_request.get("required_permission") in self.target.permissions):
                raise InputError("权限阻塞不能引用本轮已经具有的权限")
        if final_request.get("status") == "passed":
            declared_steps: set[int] = set()
            expected: set[int] = set()
            preconditions: set[int] = set()
            action_steps: set[int] = set()
            for operation, request in steps:
                if request.get("scope") == "step" and (operation == "action" or (operation == "observe" and request.get("covers_step") is True)):
                    declared_steps.add(integer(request["index"], "declared step"))
                if operation == "action" and request.get("scope") == "step":
                    action_steps.add(integer(request["index"], "action step"))
                elif operation == "compare":
                    if request.get("scope") == "expected":
                        expected.add(integer(request["index"], "declared expected"))
                    elif request.get("scope") == "precondition":
                        preconditions.add(integer(request["index"], "declared precondition"))
            gaps: JsonObject = coverage_gaps(original, declared_steps, expected, preconditions)
            if any(gaps.values()):
                raise InputError("拟通过用例的覆盖声明不完整：" + original.case_id + " " + canonical(gaps).decode("utf-8"))
            missing_actions: list[int] = [item.index for item in original.steps
                if step_requires_action(item.text) and item.index not in action_steps]
            if missing_actions:
                raise InputError("拟通过用例的交互步骤未声明真实 action：" + original.case_id + " " + canonical(missing_actions).decode("utf-8"))
        if final_request.get("status") != "test_inconclusive":
            return
        category: JsonValue = final_request.get("category")
        if category == "not_attempted":
            raise InputError("计划内不得出现 test_inconclusive/not_attempted；不确定只能来自真实尝试")
        if not isinstance(category, str) or category not in {"insufficient_observation", "not_constructible"}:
            raise InputError("计划内 test_inconclusive 必须显式声明 category：insufficient_observation/not_constructible")
        if not any(operation == "observe" for operation, _ in steps):
            raise InputError("不确定性收口必须挂在本例真实观测上；本例尚未出现任何 observe 步骤")
        if category == "not_constructible" and not any(operation == "action" for operation, _ in steps) and not any(
            record["event"] == "environment_blocked" for record in self.journal.records
        ):
            raise InputError("不可构造必须声明本例构造尝试或已有真实环境阻断记录")

    # 功能：静态校验计划引用与互斥前置；参数 steps 为本例步骤，references 为本批可引用的独立基线。
    # 目的：把 r7/r9 反复出现的构造错误（引用不存在观测、after_command_id 指向非最后动作、守卫未定义、重复消耗同一步骤）提前到接触 Player 之前。
    # 边界：只校验同一用例计划内已出现的事实，不预判任何运行期业务状态，也不放宽既有运行期门禁。
    def _check_plan_references(self, steps: list[tuple[str, JsonObject]], references: set[str]) -> None:
        observations: dict[str, JsonObject] = {}
        comparisons: dict[str, JsonObject] = {}
        actions: list[str] = []
        action_step_indices: set[int] = set()
        step_action_paths: dict[int, set[str | None]] = {}
        precondition_values: dict[tuple[str, int, str], bool | int | float | str] = {}
        for operation, request in steps:
            if operation == "baseline":
                reference_id: str = identifier(request["reference_id"], "plan baseline")
                if reference_id in references:
                    raise InputError("计划独立基线重复登记")
                references.add(reference_id)
            elif operation == "observe":
                if request.get("covers_step") is True and request.get("scope") == "step":
                    covered_index: int = integer(request.get("index"), "plan covered step")
                    if (step_requires_action(text(request.get("original_text"), "plan step text", trim=False))
                            and covered_index not in action_step_indices):
                        raise InputError("原步骤明确要求交互，不能用 covers_step=true 的只读观察替代真实 action")
                after: JsonValue = request.get("after_command_id")
                if actions:
                    # 本例已有动作时，读取必须显式关联最后一次动作（与运行期 _read_request 一致）。
                    if after is None:
                        raise InputError("计划内本例已有动作，读取步骤必须显式关联最后一次动作 after_command_id")
                    if str(after) != actions[-1]:
                        raise InputError("计划内读取的 after_command_id 必须指向本例最后一次动作")
                elif after is not None:
                    raise InputError("计划内本例尚无动作，读取步骤不得引用 after_command_id")
                observation_id: JsonValue = request.get("observation_id")
                if observation_id is not None:
                    name: str = identifier(observation_id, "plan observation_id")
                    if name in observations:
                        raise InputError("计划内观察 ID 重复")
                    observations[name] = request
            elif operation == "action":
                before: JsonValue = request.get("before_observation_id")
                if before is None or str(before) not in observations:
                    raise InputError("计划内动作的 before_observation_id 必须指向本例更早的观测步骤")
                before_request: JsonObject = observations[str(before)]
                if request.get("builtin") == "click_button" and before_request.get("builtin") != "buttons":
                    raise InputError("计划内置点击必须绑定本例更早的 builtin:buttons 观测")
                if before_request.get("target") != request.get("target"):
                    raise InputError("计划内动作与 before 必须属于同一当前目标")
                latest: list[str] = [name for name, value in observations.items() if value.get("target") == request.get("target")]
                if latest[-1] != before:
                    raise InputError("计划内动作不能引用同目标已被更新的旧 before")
                guards: JsonValue = request.get("guard_comparison_ids")
                if not isinstance(guards, list) or not guards:
                    raise InputError("计划内动作必须关联本例更早的守卫比较")
                for raw in guards:
                    if str(raw) not in comparisons:
                        raise InputError("计划内动作引用了本例更早步骤未定义的守卫比较")
                    guard: JsonObject = comparisons[str(raw)]
                    if guard.get("scope") != "guard" or guard.get("observation_id") != before:
                        raise InputError("计划内守卫必须是同一 before 的原步骤 guard 比较")
                if request.get("scope") == "step":
                    index: int = integer(request.get("index"), "plan action index")
                    action_step_indices.add(index)
                    path: str | None = builtin_action_path(request) if request.get("builtin") == "click_button" else None
                    prior_paths: set[str | None] = step_action_paths.setdefault(index, set())
                    if prior_paths and (path is None or None in prior_paths or path in prior_paths):
                        raise InputError("计划内同一原步骤动作重复；仅可依次操作不同完整路径的内置按钮")
                    prior_paths.add(path)
                command_id: JsonValue = request.get("command_id")
                if command_id is not None:
                    actions.append(identifier(command_id, "plan action command_id"))
            elif operation == "compare":
                expanded: JsonObject = expand_rule_basis(request)
                basis: JsonObject = object_value(expanded["basis"], "plan basis")
                if basis["kind"] == "baseline" and str(basis["reference_id"]) not in references:
                    raise InputError("计划比较引用的独立基线尚未登记，也未在更早步骤中声明")
                observation_id = request.get("observation_id")
                if observation_id is None or str(observation_id) not in observations:
                    raise InputError("计划内比较必须引用本例更早步骤已登记的观测")
                if expanded["scope"] == "precondition" and expanded["operator"] == "eq" and basis["kind"] == "literal":
                    key: tuple[str, int, str] = (str(observation_id), integer(expanded["index"], "precondition index"), str(expanded["field"]))
                    literal: bool | int | float | str = scalar(basis["value"])
                    if key in precondition_values and (type(precondition_values[key]) is not type(literal) or precondition_values[key] != literal):
                        raise InputError("同一观测的同一原前置存在互斥等值比较")
                    precondition_values[key] = literal
                before_binding: JsonValue = request.get("before")
                if isinstance(before_binding, dict):
                    before_id: JsonValue = before_binding.get("observation_id")
                    if before_id is None or str(before_id) not in observations:
                        raise InputError("计划内 delta 比较的 before 必须引用本例更早步骤已登记的观测")
                comparison_id: JsonValue = request.get("comparison_id")
                if comparison_id is not None:
                    name = identifier(comparison_id, "plan comparison_id")
                    if name in comparisons:
                        raise InputError("计划内比较 ID 重复")
                    comparisons[name] = request

    # 功能：静态校验计划级 defaults 只含已登记机械字段；参数 value 为空或严格对象，未知键直接拒绝。
    # timeout_ms 必须与运行期同界（target 的 max_timeout_ms），否则 plan-check 会把非法值漏到 run-case 才发现。
    def _parse_defaults(self, value: JsonValue) -> JsonObject:
        if value is None:
            return {}
        defaults: JsonObject = object_value(value, "plan defaults")
        keys_only(defaults, PLAN_DEFAULT_KEYS, "plan defaults")
        SecretGuard().check(defaults)
        ceiling: int = self.target.limits.max_timeout_ms if self.target is not None else Limits().max_timeout_ms
        for key, item in defaults.items():
            if key == "timeout_ms":
                integer(item, "defaults.timeout_ms", 1, ceiling)
            else:
                text(item, "defaults." + key, trim=False)
        return defaults

    # 功能：解析并静态预检单例计划；参数 plan 为已核验请求，不接触 Player、不写业务事件。
    def _parse_plan(self, plan: JsonObject) -> tuple[str, str, list[tuple[str, JsonObject]]]:
        keys_only(plan, PLAN_KEYS, "case plan", {"case_id", "steps"})
        if plan.get("schema") != PLAN_SCHEMA:
            raise InputError("单例计划 schema 不匹配")
        defaults: JsonObject = self._parse_defaults(plan.get("defaults"))
        # 单例计划顶层的 schema/defaults 只是包封字段；用例体校验与多例计划完全一致。
        body: JsonObject = {key: value for key, value in plan.items() if key not in {"schema", "defaults"}}
        return self._parse_case_body(body, set(), [0], defaults)

    # 功能：解析并静态预检多例计划；参数 plan 为已核验请求，只做静态核对，不接触 Player。
    def _parse_suite(self, plan: JsonObject) -> list[tuple[str, str, list[tuple[str, JsonObject]]]]:
        keys_only(plan, SUITE_KEYS, "case suite", {"cases"})
        if plan.get("schema") != SUITE_SCHEMA:
            raise InputError("多例计划 schema 不匹配")
        raw_cases: JsonValue = plan["cases"]
        if not isinstance(raw_cases, list) or not raw_cases or len(raw_cases) > SUITE_CASE_LIMIT:
            raise InputError("多例计划用例数非法")
        defaults: JsonObject = self._parse_defaults(plan.get("defaults"))
        seen_commands: set[str] = set()
        seen_cases: set[str] = set()
        step_total: list[int] = [0]
        references: set[str] = set(self.state.references)
        parsed: list[tuple[str, str, list[tuple[str, JsonObject]]]] = []
        for raw in raw_cases:
            body: JsonObject = object_value(raw, "suite case")
            case_id, group, steps = self._parse_case_body(body, seen_commands, step_total, defaults, references)
            if case_id in seen_cases:
                raise InputError("多例计划内用例重复；每例只允许收口一次")
            seen_cases.add(case_id)
            parsed.append((case_id, group, steps))
        return parsed

    # 功能：在一条命令内顺序执行单例计划全部步骤；参数 plan/origin_path 为已冻结计划请求，跨步骤复用同一连接。
    def invoke_plan(self, plan: JsonObject, origin_path: Path) -> JsonObject:
        SecretGuard().check(plan)
        self._request_base = origin_path.parent
        case_id, group, steps = self._parse_plan(plan)
        raw: bytes = read_regular(origin_path, self.journal.limits.input_bytes)
        parsed: JsonObject = object_value(strict_json(raw, self.journal.limits.input_bytes, bom=True), "CLI case plan")
        if canonical(parsed) != canonical(plan):
            raise IntegrityError("CLI 单例计划来源字节在登记前变化")
        self.journal.append("plan_begin", {"case_id": case_id, "group_id": group, "step_count": len(steps),
                                           "plan_sha256": digest(raw), "plan_path": str(origin_path.absolute()),
                                           "default_keys": sorted(self._parse_defaults(plan.get("defaults")))})
        self._source_integrity_valid = self.verify_sources(local_terminal=False)
        self._request_base = origin_path.parent
        self._request_origin = self.journal.origin(origin_path, raw, "binding", case_id)
        self.journal.append("request_registered", {"operation": "run-case", "call_id": new_id("call"),
                                                   "request_origin": self._request_origin}, case_id)
        results, _ = self._invoke_plan_steps(steps, {})
        return {"case_id": case_id, "group_id": group, "step_count": len(results),
                "last_operation": results[-1]["operation"], "last_result": results[-1]["result"],
                "request_origin": self._request_origin}

    # 功能：统一执行单例与批内单例步骤；参数 context 仅携带批索引及用例归属，不改变原步骤和异常门禁。
    # 各业务处理器已刷新 RunState；成功后的 CLI 元数据不影响状态，避免每步再次重放整个 journal。
    def _invoke_plan_steps(self, steps: list[tuple[str, JsonObject]], context: JsonObject) -> tuple[list[JsonObject], bool]:
        results: list[JsonObject] = []
        case_frozen: bool = False
        for index, (operation, request) in enumerate(steps):
            active: CaseState | None = self.state.cases.get(self.state.current) if self.state.current is not None else None
            if not self.state.frozen and active is not None and active.completion_pending() is not None and operation != "final":
                continue
            call_id: str = new_id("call")
            metadata: JsonObject = {"operation": operation, "call_id": call_id, "plan_index": index, **context}
            self.journal.append("cli_begin", {**metadata,
                                              "step_sha256": digest(canonical(request))})
            try:
                result: JsonObject = self._plan_step(operation, request)
                self.journal.append("cli_result", {**metadata, "ok": True, "result": result})
                results.append({"operation": operation, "ok": True, "result": result})
            except FrozenSession as exc:
                self.journal.append("cli_result", {**metadata, "ok": False, "error_kind": type(exc).__name__, "message": str(exc)})
                self._refresh()
                # 整轮冻结必须立即中止；本例用例级冻结只跳过本例后续 Player 步骤，
                # 让计划里尚未执行的 final 仍能按「真实尝试但观测不足」收口本例。
                if self.state.frozen:
                    raise
                case_frozen = True
                continue
            except HostError as exc:
                if isinstance(exc, IntegrityError) and self.state.closed is None:
                    self._freeze("来源/绑定/证据完整性异常；原文已排除，停止后续动作", "integrity", None)
                self.journal.append("cli_result", {**metadata, "ok": False, "error_kind": type(exc).__name__, "message": str(exc)})
                self._refresh()
                raise
            except (Exception, KeyboardInterrupt):
                pending: list[str] = [command_id for command_id in self.state.commands if command_id not in self.state.results]
                for command_id in pending:
                    intent: JsonObject = self.state.commands[command_id]
                    unknown: EvalReceipt = EvalReceipt("unknown", "host_after_intent", None, "宿主意外异常/中断，执行阶段未知；原异常未回显")
                    self.journal.append("command_result", {"command_id": command_id, "receipt": unknown.to_json(),
                                                           "frame": None, "observation_id": record_data(intent).get("observation_id"),
                                                           "observation_ref": None, "observation_valid": False, "observation_error": unknown.diagnostic,
                                                           "not_executed": False, "effective_timeout_ms": 0}, cast(str | None, intent["case_id"]))
                self._freeze("宿主非结构化异常/中断；不自动恢复或重放", "host_failure", pending[-1] if pending else None)
                self.journal.append("cli_result", {**metadata, "ok": False, "error_kind": "HostFailure",
                                                   "message": "宿主异常已排除；本轮已冻结"})
                self._refresh()
                raise FrozenSession("宿主异常/中断后冻结；原文已排除") from None
        return results, case_frozen

    # 功能：只读静态校验单例/多例计划；参数 plan 为待校验请求，不建连、不写业务事件、不消耗命令 ID、不冻结本轮。
    def check_plan(self, plan: JsonObject) -> JsonObject:
        SecretGuard().check(plan)
        schema: JsonValue = plan.get("schema")
        if schema == PLAN_SCHEMA:
            case_id, group, steps = self._parse_plan(plan)
            return {"schema": schema, "kind": "plan", "case_id": case_id, "group_id": group,
                    "step_count": len(steps), "operations": [operation for operation, _ in steps],
                    "default_keys": sorted(self._parse_defaults(plan.get("defaults"))),
                    "planning_summary": planning_summary([(case_id, group, steps)], self.cases),
                    "player_contacted": False, "journal_written": False}
        if schema == SUITE_SCHEMA:
            parsed: list[tuple[str, str, list[tuple[str, JsonObject]]]] = self._parse_suite(plan)
            return {"schema": schema, "kind": "suite", "case_count": len(parsed),
                    "case_ids": [case_id for case_id, _, _ in parsed],
                    "step_count": sum(len(steps) for _, _, steps in parsed),
                    "default_keys": sorted(self._parse_defaults(plan.get("defaults"))),
                    "selfcheck": suite_reason_selfcheck(parsed),
                    "planning_summary": planning_summary(parsed, self.cases),
                    "player_contacted": False, "journal_written": False}
        raise InputError("plan-check 只接受 mono-pipeline-case-plan/1 或 mono-pipeline-case-suite/1")

    # 功能：在一条命令、一次连接内顺序执行多例计划；参数 plan/origin_path 为已冻结计划，各例独立留证并核验现场前置。
    def invoke_suite(self, plan: JsonObject, origin_path: Path) -> JsonObject:
        SecretGuard().check(plan)
        self._request_base = origin_path.parent
        parsed: list[tuple[str, str, list[tuple[str, JsonObject]]]] = self._parse_suite(plan)
        selfcheck: list[str] = suite_reason_selfcheck(parsed)
        raw: bytes = read_regular(origin_path, self.journal.limits.input_bytes)
        stored: JsonObject = object_value(strict_json(raw, self.journal.limits.input_bytes, bom=True), "CLI case suite")
        if canonical(stored) != canonical(plan):
            raise IntegrityError("CLI 多例计划来源字节在登记前变化")
        self.journal.append("suite_begin", {"case_count": len(parsed),
                                            "case_ids": [case_id for case_id, _, _ in parsed],
                                            "step_count": sum(len(steps) for _, _, steps in parsed),
                                            "plan_sha256": digest(raw), "plan_path": str(origin_path.absolute()),
                                            "default_keys": sorted(self._parse_defaults(plan.get("defaults")))})
        self._source_integrity_valid = self.verify_sources(local_terminal=False)
        self._request_base = origin_path.parent
        # 多例计划跨例共享，按 input 类别登记；每例证据仍各自私有归属，不跨例共享。
        self._request_origin = self.journal.origin(origin_path, raw, "input", None)
        self.journal.append("request_registered", {"operation": "run-suite", "call_id": new_id("call"),
                                                   "request_origin": self._request_origin})
        cases: list[JsonObject] = []
        for case_index, (case_id, group, steps) in enumerate(parsed):
            results, case_frozen_flag = self._invoke_plan_steps(steps, {"suite_index": case_index, "case_id": case_id})
            final: JsonObject | None = results[-1]["result"] if results and results[-1]["operation"] == "final" else None
            if final is None:
                raise InputError("多例计划本例未产生真实 final，不能拿最后一个操作回执冒充结果")
            cases.append({"case_id": case_id, "group_id": group, "step_count": len(results),
                          "status": final.get("status") if final is not None else "test_inconclusive",
                          "final_result": final, "case_frozen": case_frozen_flag})
        return {"case_count": len(cases), "cases": cases, "request_origin": self._request_origin,
                "selfcheck": selfcheck,
                "statuses": [case["status"] for case in cases]}

    # 功能：执行原计划步骤；参数 request 保持原字节，真实只读脚本失败后仅本例停止并以真实证据收口。
    # 动作未知/身份/协议/来源问题不走此分支；它们仍冻结整轮，绝不重放或接触第二个 Player。
    def _plan_step(self, operation: str, request: JsonObject) -> JsonObject:
        if self.state.frozen:
            raise FrozenSession("本轮已冻结；计划立即停止，不重放未知动作")
        item: CaseState | None = self.state.cases.get(self.state.current) if self.state.current is not None else None
        if item is not None and item.frozen:
            if operation != "final":
                raise FrozenSession("本例只读脚本失败，跳过剩余步骤；原计划和请求未改写")
            return self._final({"status": "test_inconclusive", "category": "insufficient_observation",
                                "reason": "本例真实只读脚本失败；宿主停止本例后续步骤，不声明原计划通过：" + item.freeze_reason})
        if operation == "final" and item is not None and item.completion_pending() is not None:
            return self._final({"status": "test_inconclusive", "category": "insufficient_observation",
                "reason": "本例声明的业务完成条件在预算内未确认；停止剩余动作与结果断言，保留原步骤缺口；已有有效反例仍锁存。关联动作：" + str(item.completion_pending())})
        return self._handler(operation)(request)

    # 功能：重验目标后建立本命令内唯一正常连接；参数无，已有可用连接直接复用，不重复建连。
    def _connect(self) -> Pipeline:
        self._active(player=True)
        if self.target is None:
            raise IntegrityError("明确目标未加载")
        existing: Pipeline | None = self._pipeline
        if existing is not None and existing.identity is not None and existing.transport is not None:
            return existing
        pipeline: Pipeline = Pipeline(self.target, self.hooks, self.factory)
        try:
            identity: JsonObject = pipeline.connect()
            self.journal.use_guard(pipeline.guard)
            self.journal.append("connection_checked", {"identity": identity})
            self._pipeline = pipeline
            return pipeline
        except (HostError, OSError, ValueError, TypeError, MemoryError) as exc:
            # MemoryError = 本机内存不足导致的身份/包核验失败，归为环境阻塞而非宿主未知失败（2026-11-03）。
            pipeline.close()
            safe_reason: str = pipeline.guard.diagnostic(str(exc)) if isinstance(exc, HostError) else "本地身份/传输异常，原文已排除"
            self.journal.append("environment_blocked", {"reason": safe_reason, "error_kind": type(exc).__name__,
                                                        "stage": "permission_package_acl_identity_capabilities"}, self.state.current)
            if self.state.attached:
                self._freeze("已有会话的目标/连接重验失败；不接管新身份", "identity_or_connection", None)
            raise EnvironmentBlocked("明确目标未通过身份和能力核验；原异常/凭据已排除") from None

    # 功能：释放本命令内的正常连接；参数无，不结束 Player、不影响已写证据。
    def _release(self, pipeline: Pipeline) -> None:
        if self._pipeline is pipeline:
            self._pipeline = None
        pipeline.close()

    # 功能：检查全轮命令 ID 和明确编译更正；参数 request 不允许执行同一 ID 两次。
    def _command_id(self, request: JsonObject, mode: str, case_id: str | None) -> str:
        command_id: str = identifier(request.get("command_id"), "command_id")
        if command_id in self.state.commands:
            raise InputError("该命令 ID 已登记；绝不重放，编译更正也必须使用新 ID")
        correction: JsonValue = request.get("correction_of")
        if correction is not None:
            previous_id: str = identifier(correction, "correction_of")
            previous: JsonObject | None = self.state.results.get(previous_id)
            if previous is None or record_data(previous).get("receipt") is None:
                raise InputError("更正必须引用已有明确编译失败回执")
            receipt: JsonObject = object_value(record_data(previous)["receipt"], "correction receipt")
            prior: JsonObject = record_data(self.state.commands[previous_id])
            if receipt.get("state") != "compile_failed" or previous["case_id"] != case_id or prior.get("mode") != mode:
                raise InputError("只允许明确未执行的编译错误更正；未知/成功不得重放")
            text(request.get("correction_reason"), "correction_reason", trim=False)
            for key in ("scope", "index", "target"):
                if request.get(key) != prior.get(key):
                    raise InputError("编译更正不能改变原步骤/目标绑定")
        return command_id

    # 功能：执行一个已登记短片段，保存用户及实际包装字节；参数 request 来自当前现场请求。
    def _run_script(self, pipeline: Pipeline, request: JsonObject, mode: str,
                    case_id: str | None, raw_builtin: bytes | None = None,
                    timeout_cap_ms: int | None = None, poll_deadline: float | None = None) -> JsonObject:
        if self.target is None:
            raise IntegrityError("目标配置未加载")
        command_id: str = self._command_id(request, mode, case_id)
        timeout: int = integer(request.get("timeout_ms", self.target.limits.script_timeout_ms), "script timeout", 1, self.target.limits.max_timeout_ms)
        if timeout_cap_ms is not None:
            timeout = min(timeout, integer(timeout_cap_ms, "remaining poll budget", 1, self.target.limits.max_timeout_ms))
        send: str = str(request.get("send", "eval_file"))
        if send not in {"eval", "eval_file"}:
            raise InputError("send 只能为 eval/eval_file")
        try:
            pipeline.preflight()
        except HostError:
            self._release(pipeline)
            self._freeze("发送前身份重验失败，未发当前脚本且不接管新身份", "identity_preflight", None)
            raise EnvironmentBlocked("发送前目标/凭据身份重验失败；整轮停止") from None
        # 设备侧命名观测：由宿主按已登记 op 生成方法体，替代 Agent 现场手写 C#；仍走同一包装/门禁/证据链。
        if raw_builtin is None and request.get("builtin") is not None:
            raw_builtin = builtin_observation(str(request.get("builtin")),
                                              object_value(request.get("builtin_options", {}), "builtin_options"))
        script_path: Path | None = None if raw_builtin is not None else local_path(text(request.get("script"), "script"), self._request_base)
        if script_path is not None and script_path.suffix.lower() != ".cs":
            raise InputError("用户脚本文件必须为 .cs 方法体")

        # 功能：冻结原字节并发送一次；参数 raw 在源文件保护句柄内，eval_file 另持包装句柄。
        def execute_held(raw: bytes) -> JsonObject:
            wrapper: bytes = wrap_script(raw, self.journal.run_id, case_id or "", command_id, self.target.limits, pipeline.guard)
            evidence_case: str = case_id if case_id is not None else CONTROL_CASE
            builtin_name: JsonValue = request.get("builtin")
            source: JsonObject = {"kind": "user_script" if script_path else (("builtin_action" if mode == "action" else "builtin_observation") if builtin_name is not None else "host_builtin"),
                                  "path": str(script_path) if script_path else ("builtin:" + str(builtin_name) if builtin_name is not None else "runtime_mono_development_probe"),
                                  "command_id": command_id, "sha256": digest(raw)}
            if builtin_name is not None and mode == "action":
                source["options"] = request.get("builtin_options")
            original_ref: JsonObject = self.journal.store("script_original", raw, source, evidence_case, ".cs")
            wrapper_ref: JsonObject = self.journal.store("script_wrapper", wrapper, {
                "kind": "host_wrapper", "command_id": command_id, "original_sha256": digest(raw),
            }, evidence_case, ".cs")
            declared_timeout: int = timeout
            if poll_deadline is not None:
                declared_timeout = max(1, min(timeout, int((poll_deadline - time.perf_counter()) * 1000)))
            intent_data: JsonObject = {
                "command_id": command_id, "mode": mode, "scope": request.get("scope"), "index": request.get("index"),
                "original_text": request.get("original_text"), "target": request.get("target"),
                "value_format": request.get("value_format", "json"), "purpose": request.get("purpose"),
                "observation_id": request.get("observation_id"), "after_command_id": request.get("after_command_id"),
                "covers_step": request.get("covers_step", False), "reason": request.get("reason"),
                "read_only_review": request.get("read_only_review"), "before_observation_id": request.get("before_observation_id"),
                "guard_comparison_ids": request.get("guard_comparison_ids", []), "request_origin": self._request_origin,
                "script_original": original_ref, "script_wrapper": wrapper_ref, "source_sha256": digest(raw),
                "sent_sha256": digest(wrapper), "send": send, "timeout_ms": declared_timeout,
                "correction_of": request.get("correction_of"), "correction_reason": request.get("correction_reason"),
            }
            # intent + 原字节 + 实际包装均先 fsync，再允许任何 HTTP eval 请求。
            self.journal.append("intent", intent_data, case_id)
            receipt: EvalReceipt
            actual_timeout: int = declared_timeout
            wrapper_path: Path = self.journal.root / str(wrapper_ref["path"])
            try:
                if poll_deadline is not None:
                    actual_timeout = min(actual_timeout, int((poll_deadline - time.perf_counter()) * 1000))
                if actual_timeout <= 0:
                    receipt = EvalReceipt("not_sent", "poll_budget_not_sent", None, "本例轮询总预算已用尽，未发下一读取")
                elif send == "eval_file":
                    with protected_file(wrapper_path, self.target.limits.wrapper_bytes, digest(wrapper)):
                        remaining: int = actual_timeout if poll_deadline is None else min(actual_timeout, int((poll_deadline - time.perf_counter()) * 1000))
                        if remaining <= 0:
                            actual_timeout = 0
                            receipt = EvalReceipt("not_sent", "poll_budget_not_sent", None, "本例轮询总预算已用尽，未发下一读取")
                        else:
                            actual_timeout = remaining
                            receipt = pipeline.execute(wrapper, remaining, wrapper_path)
                else:
                    receipt = pipeline.execute(wrapper, actual_timeout)
            except (HostError, OSError):
                receipt = EvalReceipt("not_sent", "file_protection_not_sent", None, "包装文件保护失败，HTTP 未发送")
            frame: int | None = None
            value: JsonValue = None
            error: str = ""
            valid: bool = False
            if receipt.state == "succeeded":
                try:
                    frame, value, error = observed_value(receipt, self.journal.run_id, case_id or "", command_id,
                                                          self.target.build_guid, str(request.get("value_format", "json")),
                                                          request.get("target"), self.target.limits, wrapper_format(wrapper))
                    pipeline.guard.check(value)
                    if mode in {"action", "probe"} and error:
                        receipt = EvalReceipt("unknown", "return_value_contract" if error.startswith("return_value_contract:") else "bridge_action_error", None, error)
                    else:
                        valid = not error and value is not None
                        if value is None and not error and mode == "read":
                            error = "目标实际值为空，不当作 false/0"
                except IntegrityError:
                    value = None
                    receipt = EvalReceipt("unknown", "identity_or_sensitive_envelope", None, "实际包装/桥接身份或敏感结果不可靠；原文未保存")
                except InputError:
                    if mode == "action" or mode == "probe":
                        receipt = EvalReceipt("unknown", "identity_envelope", None, "动作/探针未取得可靠宿主信封")
                    else:
                        error = "独立观测目标/字段/桥接结构不可靠，不生成默认值"
            observation_ref: JsonObject | None = None
            observation_id: JsonValue = request.get("observation_id") if mode == "read" else None
            if mode == "read" and receipt.state == "succeeded" and case_id is not None:
                after_id: JsonValue = request.get("after_command_id")
                if after_id is not None:
                    action_result: JsonObject | None = self.state.results.get(str(after_id))
                    action_frame: JsonValue = record_data(action_result).get("frame") if action_result is not None else None
                    if type(action_frame) is not int or frame is None or frame <= action_frame:
                        valid = False
                        if not error:
                            error = "独立观测帧未晚于动作帧；旧帧不能断言"
                if isinstance(value, dict) and value and set(value) <= {"success", "assertion", "passed", "verdict"}:
                    valid = False
                    error = "脚本自述成功/断言不是独立业务值"
                snapshot: JsonObject = {"schema": SCHEMA, "run_id": self.journal.run_id, "case_id": case_id,
                                        "observation_id": observation_id, "command_id": command_id,
                                        "target": request.get("target"), "purpose": request.get("purpose"),
                                        "step_index": request.get("index"), "frame": frame, "build_guid": self.target.build_guid,
                                        "after_command_id": after_id, "valid": valid, "error": error, "value": value}
                observation_ref = self.journal.store("observation", canonical(snapshot), {
                    "kind": "independent_read", "command_id": command_id, "wrapper_sha256": digest(wrapper),
                }, case_id)
            result: JsonObject = {"command_id": command_id, "receipt": receipt.to_json(), "frame": frame,
                                  "observation_id": observation_id, "observation_ref": observation_ref,
                                  "observation_valid": valid, "observation_error": error,
                                  "not_executed": receipt.state in {"compile_failed", "not_sent"},
                                  "effective_timeout_ms": max(0, actual_timeout)}
            self.journal.append("command_result", result, case_id)
            if receipt.state == "unknown":
                # 脚本自身缺陷（phase=script_failed）只降级到用例级，但仅限有明确本例的只读命令：
                # 动作可能已部分生效，必须按整轮冻结处理，不能假设「脚本错了所以什么都没发生」。
                if receipt.phase == "script_failed" and case_id is not None and mode == "read":
                    self._freeze_case(case_id, receipt.diagnostic or "只读脚本自身缺陷导致求值失败", receipt.phase, command_id)
                else:
                    self._freeze(receipt.diagnostic or "求值结果未知，停止整轮", receipt.phase, command_id)
            elif mode == "read" and case_id is not None and error.startswith("return_value_contract:"):
                self._freeze_case(case_id, error, "return_value_contract", command_id)
            self._refresh()
            return {**result, "value": value if mode == "read" and receipt.state == "succeeded" else None}

        if script_path is None:
            if raw_builtin is None:
                raise IntegrityError("宿主脚本原字节缺失")
            return execute_held(raw_builtin)
        with protected_file(script_path, self.target.limits.script_bytes) as original:
            return execute_held(original)

    # 功能：明确附加并独立验证 Mono/Development，基础读取不依赖桥接；参数仅接受空对象。
    def _attach(self, request: JsonObject) -> JsonObject:
        keys_only(request, set(), "attach")
        pipeline: Pipeline = self._connect()
        try:
            discovery: str = builtin_observation("chain", {"names_only": True, "depth": BUILTIN_MAX_DEPTH, "max_nodes": 256}).decode("utf-8")
            result: JsonObject = self._run_script(pipeline, {
                "command_id": new_id("attach"), "send": "eval", "scope": "probe", "target": "Unity.Runtime",
                "value_format": "json", "reason": "独立确认当前 Mono Development Player",
            }, "probe", None, (
                'System.Func<object> __mpft_discover = delegate() {\n' + discovery + '\n};\n'
                'return new System.Collections.Generic.Dictionary<string, object> {\n'
                '{"mono", System.Type.GetType("Mono.Runtime") != null},\n'
                '{"development", UnityEngine.Debug.isDebugBuild}, {"discovery", __mpft_discover()}\n};\n'
            ).encode("utf-8"))
            receipt: JsonObject = object_value(result["receipt"], "attach receipt")
            if receipt["state"] != "succeeded":
                raise EnvironmentBlocked("附加探针没有可靠完成；编译诊断/未知阶段已实时记录")
            envelope: JsonObject = object_value(receipt["value"], "attach envelope")
            actual: JsonObject = object_value(envelope.get("value"), "attach actual")
            if actual.get("mono") is not True or actual.get("development") is not True:
                raise EnvironmentBlocked("当前 Player 未独立证明 Mono + Development；不得降级")
            self.journal.append("session_attached", {"probe_command_id": result["command_id"], "frame": result["frame"],
                                                     "mono": True, "development": True, "business_ready": "未声明，逐例独立观测"})
            self._refresh()
            return {"attached": True, "probe_command_id": result["command_id"], "frame": result["frame"],
                    "discovery": actual.get("discovery"), "business_ready": False}
        except BaseException:
            self._release(pipeline)
            raise

    # 功能：返回本轮现场状态，不重连/恢复；参数仅为空对象。
    def _status(self, request: JsonObject) -> JsonObject:
        keys_only(request, set(), "status")
        return {"run_id": self.journal.run_id, "attached": self.state.attached, "frozen": self.state.frozen,
                "freeze_reason": self.state.freeze_reason, "current_case": self.state.current,
                "closed": self.state.closed is not None, "command_count": len(self.state.commands),
                "source_integrity_valid": self._source_integrity_valid,
                "formal_report_eligible": self.state.closed is not None and self.state.timing is not None and not self.state.integrity_interrupted and self._source_integrity_valid,
                "binding_sources": binding_sources(self.original_case(self.state.current)) if self.cases is not None and self.state.current is not None else None,
                "chain_ready": self.state.chain_closed is not None,
                "remaining_case_ids": [original.case_id for original in self.cases.cases if original.case_id not in self.state.cases] if self.cases is not None else [],
                "completion_pending": {case_id: item.completion_pending() for case_id, item in self.state.cases.items()
                                       if item.completion_pending() is not None},
                "finals": {case_id: record_data(item.final)["status"] for case_id, item in self.state.cases.items() if item.final is not None}}

    # 功能：在首条业务用例前登记独立共享准备；参数 request 为完整来源与真实审阅，dry_run 不登记、不接触 Player。
    def _chain_start(self, request: JsonObject, dry_run: bool = False) -> JsonObject:
        self._active()
        if not self.state.attached or self.target is None or self.cases is None:
            raise EnvironmentBlocked("共享链路必须先附加并独立证明 Mono Development 目标")
        if self.state.frozen or self.state.cases or self.state.current is not None:
            raise InputError("共享链路只允许在首条原用例前建立一次，不恢复或覆盖旧准备")
        if any(original.case_id.casefold() == CONTROL_CASE.casefold() for original in self.cases.cases):
            raise InputError("原用例使用了保留控制编号，不能与共享准备混淆")
        original: OriginalCase = parse_chain_source(request, self.target.limits)
        result: JsonObject = {"source_kind": "input", "business_case_count_unchanged": True,
                              "binding_sources": binding_sources(original), "ready": False}
        if dry_run:
            return result
        data: JsonObject = {"source": request, "source_kind": "input", "group_id": "session-chain",
                            "request_origin": self._request_origin}
        reference: JsonObject = self.journal.store("input", canonical(data), {"kind": "shared_setup_input"}, CONTROL_CASE)
        self.journal.append("chain_started", {**data, "evidence": reference}, CONTROL_CASE)
        self._refresh()
        return {**result, "evidence": reference}

    # 功能：独立验证全部准备步骤、条件与预期后闭合共享链路；参数只允许空对象，dry_run 不写事件或业务 final。
    def _chain_end(self, request: JsonObject, dry_run: bool = False) -> JsonObject:
        keys_only(request, set(), "chain-end")
        if self.state.current != CONTROL_CASE or self.state.chain_original is None or self.state.chain_closed is not None:
            raise InputError("没有唯一活动共享链路可收口")
        gate_error: str | None = chain_action_gate_error(self.state.chain_original,
            self.state.cases[CONTROL_CASE], self.state.commands)
        if gate_error is not None:
            raise InputError(gate_error)
        checked: JsonObject = self._final({"status": "passed"}, dry_run=True)
        if checked["status"] != "passed":
            raise InputError("共享准备存在独立反例，不能声明链路就绪")
        data: JsonObject = {"ready": True, "coverage": checked["coverage"],
                            "comparison_ids": checked["comparison_ids"], "observation_ids": checked["observation_ids"],
                            "action_command_ids": checked["action_command_ids"], "start_seq": checked["start_seq"],
                            "start_hash": checked["start_hash"], "request_origin": self._request_origin}
        if dry_run:
            return data
        reference: JsonObject = self.journal.store("binding", canonical(data), {"kind": "shared_setup_verified"}, CONTROL_CASE)
        self.journal.append("chain_closed", {**data, "evidence": reference}, CONTROL_CASE)
        self._refresh()
        return {**data, "evidence": reference}

    # 功能：开始一个完整原用例，不要求动作映射；参数 case_id/group_id 为当前 AI 选择。
    def _start(self, request: JsonObject) -> JsonObject:
        keys_only(request, {"case_id", "group_id"}, "start-case", {"case_id"})
        self._active()
        if self.state.frozen or self.state.current is not None or self.cases is None:
            raise InputError("冻结/已有活动例时不能开始新例")
        if self.state.chain_original is not None and self.state.chain_closed is None:
            raise InputError("共享准备尚未独立验证，不能进入原业务用例")
        case_id: str = text(request["case_id"], "case_id")
        original: OriginalCase = self.cases.case(case_id)
        if case_id in self.state.cases:
            raise InputError("原用例已经开始或 final，禁止重跑覆盖")
        group: str = text(request.get("group_id", "ungrouped"), "group_id")
        self.journal.append("case_started", {"title": original.title, "group_id": group}, case_id)
        self._refresh()
        return {"case_id": case_id, "original_case": original.raw, "group_id": group,
                "binding_sources": binding_sources(original),
                "request_policy": "每次提交使用新文件；登记后即使 InputError 也不可改写。更正另建文件及新 ID，不重放"}

    # 功能：验证现场只读请求与原索引；参数 request 不要求预制定位映射，允许设备侧命名观测 op 替代手写脚本。
    def _read_request(self, request: JsonObject) -> tuple[str, OriginalCase, CaseState, JsonObject]:
        keys_only(request, {"command_id", "observation_id", "script", "builtin", "builtin_options", "send", "scope",
                            "index", "original_text", "purpose", "target", "read_only_review", "reason", "covers_step",
                            "after_command_id", "value_format", "timeout_ms", "poll", "correction_of", "correction_reason"},
                  "observe", {"command_id", "observation_id", "purpose", "target", "read_only_review", "reason"})
        self._active(player=True)
        if not self.state.attached:
            raise EnvironmentBlocked("必须先明确附加并独立验证当前 Mono Development Player")
        case_id, original, item = self._current()
        if case_id == CONTROL_CASE and not item.observations and request.get("builtin") != "chain":
            raise InputError("共享链路必须以一次 builtin:chain 观测开始，不逐节点试探")
        self._command_id(request, "read", case_id)
        # 设备侧命名观测与手写脚本互斥：有 builtin 就不允许再给 script，反之亦然。
        builtin: JsonValue = request.get("builtin")
        if builtin is not None:
            name: str = text(builtin, "builtin")
            if name not in BUILTIN_OBSERVATIONS:
                raise InputError("未知设备侧观测 op；只允许 chain/subtree/buttons/logic_field/member_probe")
            if request.get("script") is not None:
                raise InputError("设备侧命名观测与手写脚本不能同时出现")
            options: JsonObject = object_value(request.get("builtin_options", {}), "builtin_options")
            builtin_observation(name, options)
        elif request.get("builtin_options") is not None:
            raise InputError("builtin_options 只能与 builtin 同时出现")
        elif request.get("script") is None:
            raise InputError("observe 必须给出 script 或 builtin 之一")
        observation_id: str = identifier(request["observation_id"], "observation_id")
        if observation_id in item.observations or any(record_data(trace).get("observation_id") == observation_id and trace["case_id"] == case_id for trace in self.state.commands.values()):
            raise InputError("观察 ID 已登记，不能覆盖")
        purpose: str = text(request["purpose"], "read purpose")
        if purpose not in READ_PURPOSES:
            raise InputError("读取用途不在已知只读契约内")
        if purpose == "logs" and self.target is not None and "log_read" not in self.target.permissions:
            raise EnvironmentBlocked("运行时日志观测还要求 log_read 许可")
        text(request["read_only_review"], "read_only_review", trim=False)
        text(request["reason"], "reason", trim=False)
        target: JsonValue = request["target"]
        if not ((isinstance(target, str) and target.strip()) or (isinstance(target, dict) and target)):
            raise InputError("只读观察必须有明确当前目标，缺目标不采用默认值")
        scope: str = str(request.get("scope", "discovery"))
        if scope not in {"step", "precondition", "guard", "discovery"}:
            raise InputError("观察原索引范围非法")
        normalized: JsonObject = {**request, "scope": scope}
        if scope != "discovery":
            index: int = integer(request.get("index"), "source index")
            source_text: str = original.item(scope, index).text
            if request.get("original_text") != source_text:
                raise InputError("只读绑定原索引/原文不匹配")
        elif request.get("index") is not None or request.get("original_text") is not None:
            raise InputError("现场 discovery 不能冒充原步骤覆盖")
        covers: JsonValue = request.get("covers_step", False)
        if type(covers) is not bool or (covers and (scope != "step" or purpose not in {"step", "after"})):
            raise InputError("只读步骤覆盖必须显式关联原 step，且不能用 discovery 代替")
        if covers and step_requires_action(original.item("step", integer(request.get("index"), "read step index")).text):
            step_index: int = integer(request.get("index"), "read step index")
            matching_action: bool = any(
                record_data(self.state.commands[action_id]).get("mode") == "action"
                and record_data(self.state.commands[action_id]).get("scope") == "step"
                and record_data(self.state.commands[action_id]).get("index") == step_index
                for action_id in item.actions if action_id in self.state.commands
            )
            if not matching_action:
                raise InputError("原步骤明确要求交互，不能用 covers_step=true 的只读观察替代真实 action")
        if item.actions:
            after_id: str = identifier(request.get("after_command_id"), "after_command_id")
            if after_id != item.actions[-1]:
                raise InputError("动作之后的读取必须显式关联本例最后一次动作，不读旧阶段")
        elif request.get("after_command_id") is not None:
            raise InputError("独立读取引用了本例不存在的动作")
        return case_id, original, item, normalized

    # 功能：只读执行或有总预算的新帧轮询；参数 poll 仅控制早停，不形成业务 verdict。
    def _observe(self, request: JsonObject) -> JsonObject:
        case_id, original, item, normalized = self._read_request(request)
        if self.target is None:
            raise IntegrityError("目标未加载")
        condition: JsonObject | None = poll_condition(request.get("poll"), request.get("after_command_id"))
        start_record: JsonObject | None = None
        if condition is not None:
            start_record = self.journal.append("poll_started", {"poll_id": request["command_id"],
                                                               "budget_ms": self.target.limits.poll_budget_ms,
                                                               "condition": condition}, case_id)
        pipeline: Pipeline = self._connect()
        # 总预算自建连与身份核验完成后起算：建连/包核验不是等待新帧的时间，计入会让首样本只剩残余预算（2026-11-04 实机 d126）。
        deadline: float = time.perf_counter() + self.target.limits.poll_budget_ms / 1000
        results: list[JsonObject] = []
        stable: int = 0
        last_frame: int = -1
        matched: bool = False
        poll_error: str = ""
        # 本次轮询已观测的最慢单样本耗时（毫秒，含发送前身份重验）；用于判断剩余预算是否还够完成下一样本。
        slowest_ms: int = 0
        budget_short: bool = False
        try:
            samples: int = self.target.limits.poll_samples if condition is not None else 1
            for sample in range(samples):
                remaining: int = int((deadline - time.perf_counter()) * 1000)
                if condition is not None and remaining <= 0:
                    break
                # 剩余预算不足以完成下一样本时不再发送：注定超时的样本会得到 unknown 回执并冻结整轮，改为转入确认读取。
                if condition is not None and results and remaining < slowest_ms:
                    budget_short = True
                    break
                current: JsonObject = dict(normalized)
                # 轮询样本一律使用宿主派生 ID；计划声明的命令/观察 ID 留给轮询结束后的确认读取，保证后续比较/动作引用的是最新帧。
                if condition is not None:
                    current["command_id"] = new_id("poll-read")
                    current["observation_id"] = new_id("obs")
                    current.pop("correction_of", None)
                    current.pop("correction_reason", None)
                began: float = time.perf_counter()
                result: JsonObject = self._run_script(pipeline, current, "read", case_id,
                                                      timeout_cap_ms=min(remaining, self.target.limits.max_timeout_ms) if condition is not None else None,
                                                      poll_deadline=deadline if condition is not None else None)
                slowest_ms = max(slowest_ms, int((time.perf_counter() - began) * 1000))
                results.append(result)
                receipt: JsonObject = object_value(result["receipt"], "read receipt")
                if receipt["state"] != "succeeded" or condition is None or not self._poll_confirm_allowed(case_id):
                    break
                if result["observation_valid"] is True:
                    try:
                        actual: JsonValue = field_value(result.get("value"), str(condition["field"]))
                        now_matches, ignored = compare_values(str(condition["operator"]), actual, condition["value"])
                        frame: int = integer(result["frame"], "poll frame", 0)
                        if frame > last_frame:
                            stable = stable + 1 if now_matches else 0
                            last_frame = frame
                        if stable >= integer(condition.get("stable_samples", 1), "stable_samples", 1, 8):
                            matched = True
                            break
                    except InputError:
                        poll_error = "轮询早停字段/类型不足，不当作反例或默认值"
                        break
                elif condition.get("require_match") is True:
                    stable = 0
                remaining_seconds: float = deadline - time.perf_counter()
                if remaining_seconds <= 0:
                    break
                time.sleep(min(self.target.limits.poll_interval_ms / 1000, remaining_seconds))
            last_state: JsonValue = object_value(results[-1]["receipt"], "poll receipt").get("state") if results else "not_sent"
            if condition is not None and last_state in {"succeeded", "not_sent"} and self._poll_confirm_allowed(case_id):
                # 确认读取：以计划声明的命令/观察 ID 再读一次新帧，单次脚本超时，不重置也不延长轮询早停预算。
                results.append(self._run_script(pipeline, dict(normalized), "read", case_id))
            if condition is not None and condition.get("require_match") is True and start_record is not None:
                current_item: CaseState | None = self.state.cases.get(case_id)
                if current_item is None:
                    raise IntegrityError("业务完成确认缺少当前用例状态")
                matched = completion_confirmed(current_item, condition, str(request["command_id"]), integer(start_record["seq"], "poll start seq"))
                if not matched and not poll_error:
                    poll_error = "实际稳定样本或最终确认帧未满足业务完成条件"
            actual_observations: list[JsonObject] = [result for result in results if result.get("observation_ref") is not None]
            last_observation_id: JsonValue = actual_observations[-1]["observation_id"] if actual_observations else None
            if start_record is not None:
                closed_reason: str = ("剩余总预算不足以完成下一样本（按本次已观测最慢样本耗时），提前转确认读取，未发送注定超时的样本；仍需独立原预期比较"
                                      if budget_short else "总预算/样本上限/未知阶段到达；仍需独立原预期比较")
                self.journal.append("poll_closed", {"poll_id": request["command_id"], "start_seq": start_record["seq"],
                                                    "sample_count": len(results), "matched": matched,
                                                    "last_observation_id": last_observation_id,
                                                    "diagnostic": poll_error or ("" if matched else closed_reason)}, case_id)
                if condition is not None and condition.get("require_match") is True:
                    self._refresh()
            return {"samples": results, "last_observation_id": last_observation_id,
                    "poll_matched": matched if condition is not None else None,
                    "completion_required": condition is not None and condition.get("require_match") is True,
                    "product_verdict": "not_compared", "frozen": self.state.frozen,
                    "case_frozen": self.state.cases[case_id].frozen}
        except BaseException:
            self._release(pipeline)
            raise

    # 功能：判断轮询结束后是否允许以声明 ID 做一次确认读取；参数 case_id 为本例编号，整轮或本例冻结后不再发送。
    def _poll_confirm_allowed(self, case_id: str | None) -> bool:
        if self.state.frozen or self.state.closed is not None:
            return False
        item: CaseState | None = self.state.cases.get(case_id) if case_id is not None else None
        return item is None or not item.frozen

    # 功能：根据当前定位/守卫/合法前置只执行一次动作；参数 request 的 before/guard 均来自本例实际读取。
    def _check_action(self, request: JsonObject) -> bytes | None:
        allowed: set[str] = {"command_id", "script", "builtin", "builtin_options", "send", "scope", "index", "original_text", "target",
                             "before_observation_id", "guard_comparison_ids", "target_review", "reason",
                             "value_format", "timeout_ms", "correction_of", "correction_reason"}
        keys_only(request, allowed, "action", {"command_id", "scope", "index", "original_text", "target",
                                               "before_observation_id", "guard_comparison_ids", "target_review", "reason"})
        self._active(player=True)
        if not self.state.attached or self.target is None:
            raise EnvironmentBlocked("动作必须使用已独立验证的明确附加目标")
        case_id, original, item = self._current()
        scope: str = text(request["scope"], "action.scope")
        if item.completion_pending() is not None:
            raise InputError("业务完成条件尚未确认；先只读确认或收口本例，不继续发送动作")
        if scope not in {"step", "precondition"}:
            raise InputError("动作只能关联原 step 或合法前置构造")
        index: int = integer(request["index"], "action.index")
        if request["original_text"] != original.item(scope, index).text:
            raise InputError("动作原步骤/前置文本绑定发生变化")
        permission: str = "business_action" if scope == "step" and case_id != CONTROL_CASE else "setup_action"
        if permission not in self.target.permissions:
            raise EnvironmentBlocked("动作缺少相应显式业务/前置构造许可")
        self._command_id(request, "action", case_id)
        prior_actions: list[JsonObject] = [record_data(self.state.commands[command_id]) for command_id in item.actions
            if scope == "step" and record_data(self.state.commands[command_id]).get("scope") == "step"
            and record_data(self.state.commands[command_id]).get("index") == index]
        if prior_actions and request.get("builtin") != "click_button":
            raise InputError("本例该原步骤动作重复；只有不同内置按钮可继续必要交互")
        before_id: str = identifier(request["before_observation_id"], "before_observation_id")
        before: JsonObject | None = item.observations.get(before_id)
        if before is None or before.get("valid") is not True or before.get("target") != request["target"]:
            raise InputError("动作缺少当前唯一目标的有效本例 before 观测")
        target_observations: list[JsonObject] = [value for value in item.observations.values() if value.get("target") == request["target"]]
        if target_observations and target_observations[-1].get("observation_id") != before_id:
            raise InputError("同目标已有更新观察，不能使用被覆盖的旧 before/守卫")
        text(request["target_review"], "target_review", trim=False)
        text(request["reason"], "action.reason", trim=False)
        if item.actions:
            action_frame: int = integer(record_data(self.state.results[item.actions[-1]]).get("frame"), "last action frame", 0)
            if integer(before.get("frame"), "before frame", 0) <= action_frame or before.get("after_command_id") != item.actions[-1]:
                raise InputError("继续动作前必须先取得上一动作之后的独立新帧观测")
        guards: JsonValue = request["guard_comparison_ids"]
        if not isinstance(guards, list) or not guards or len(set(str(value) for value in guards)) != len(guards):
            raise InputError("动作必须关联独立通过的当前业务守卫比较")
        for raw in guards:
            comparison: JsonObject | None = item.comparisons.get(identifier(raw, "guard comparison"))
            if comparison is None:
                raise InputError("动作引用不存在的守卫比较")
            binding: JsonObject = object_value(comparison.get("binding"), "guard binding")
            if binding.get("scope") != "guard" or binding.get("observation_id") != before_id or comparison.get("valid") is not True or comparison.get("matched") is not True:
                raise InputError("守卫不是同一当前目标 before 的独立有效通过比较")
        preconditions: dict[int, JsonObject] = {}
        for comparison in item.comparisons.values():
            binding = object_value(comparison["binding"], "precondition binding")
            if binding.get("scope") == "precondition":
                preconditions[integer(binding.get("index"), "precondition index")] = comparison
        if scope == "precondition":
            prior: JsonObject | None = preconditions.get(index)
            if prior is None or prior.get("valid") is not True or prior.get("matched") is not False:
                raise InputError("合法前置构造必须先独立读出本例该原前置未满足")
        elif not any(record_data(self.state.commands[command_id]).get("scope") == "step" for command_id in item.actions):
            for condition in original.preconditions:
                prior = preconditions.get(condition.index)
                if prior is None or prior.get("valid") is not True or prior.get("matched") is not True:
                    raise EnvironmentBlocked("原关键前置尚未独立满足；不得先执行业务动作")
                observation: JsonObject = item.observations[str(object_value(prior["binding"], "precondition binding")["observation_id"])]
                if item.actions and integer(observation.get("frame"), "precondition frame", 0) <= integer(record_data(self.state.results[item.actions[-1]]).get("frame"), "setup action frame", 0):
                    raise InputError("前置构造后必须独立新帧精确回读，再执行原业务步骤")
        if request.get("builtin") is not None:
            before_command: JsonObject = record_data(self.state.commands[str(before["command_id"])])
            source: JsonObject = object_value(object_value(before_command["script_original"], "before script")["source"], "before source")
            if source.get("kind") != "builtin_observation" or source.get("path") != "builtin:buttons":
                raise InputError("内置点击只接受宿主生成的 builtin:buttons，不能采用手写伪同名值")
            path: str = builtin_action_path(request)
            row: JsonObject = builtin_button_row(path, before)
            for prior_action in prior_actions:
                prior_source: JsonObject = object_value(object_value(prior_action["script_original"], "prior script")["source"], "prior source")
                if prior_source.get("kind") != "builtin_action" or prior_source.get("path") != "builtin:click_button":
                    raise InputError("本例该原步骤动作重复；不能混用手写脚本继续同一步")
                prior_path: str = text(object_value(prior_source["options"], "prior options")["path"], "prior path")
                prior_row: JsonObject = builtin_button_row(prior_path, item.observations[str(prior_action["before_observation_id"])])
                if path == prior_path or row["instance_id"] == prior_row["instance_id"] or row["node_instance_id"] == prior_row["node_instance_id"]:
                    raise InputError("本例该原步骤按钮路径或实例重复；换 ID 不能重放")
            return builtin_button_click(object_value(request.get("builtin_options"), "builtin_options"), before)
        return None
    # 功能：通过共用的当前 before/guard/前置核验后发送一次动作；参数 request 不以回执作为产品断言。
    def _action(self, request: JsonObject) -> JsonObject:
        raw_builtin: bytes | None = self._check_action(request)
        case_id, original, item = self._current()
        pipeline: Pipeline = self._connect()
        try:
            return self._run_script(pipeline, request, "action", case_id, raw_builtin)
        except BaseException:
            self._release(pipeline)
            raise

    # 功能：校验原文、实际字段和独立预期依据；参数 request 每条绑定由当前 Agent 语义审核。
    def _binding(self, request: JsonObject, original: OriginalCase, item: CaseState) -> tuple[JsonObject, JsonValue]:
        canonical_fields: set[str] = {"schema", "comparison_id", "scope", "index", "original_text", "step_indices",
                                      "observation_id", "field", "operator", "basis", "before"}
        # rule 简写在此展开为与手写完全等价的 field/operator/basis；审计与 journal 只见展开结果，等价性由同一后续校验保证。
        request = expand_rule_basis(request)
        fields: set[str] = canonical_fields
        keys_only(request, fields, "comparison", fields - {"step_indices", "before"})
        if request["schema"] != "mono-pipeline-comparison/1":
            raise InputError("比较 schema 不匹配")
        comparison_id: str = identifier(request["comparison_id"], "comparison_id")
        if comparison_id in item.comparisons:
            raise InputError("比较 ID 已登记；不能静默修改绑定或覆盖失败")
        scope: str = text(request["scope"], "comparison.scope")
        if scope not in {"expected", "precondition", "guard"}:
            raise InputError("比较必须关联原预期/前置/原步骤守卫")
        index: int = integer(request["index"], "comparison.index")
        if request["original_text"] != original.item(scope, index).text:
            raise InputError("比较原索引或原预期文本不匹配；从 start-case/status.binding_sources 取本 scope 的完整原文，"
                             "guard 取原步骤而非前置。更正必须新请求文件和新比较 ID，不可改写已登记文件")
        steps: JsonValue = request.get("step_indices", [index] if scope == "guard" else [])
        if not isinstance(steps, list) or (scope == "expected" and not steps):
            raise InputError("每条原预期必须声明本例相关原步骤索引")
        indexes: list[int] = [integer(value, "bound step index") for value in steps]
        if len(set(indexes)) != len(indexes):
            raise InputError("原预期步骤索引重复")
        for step in indexes:
            original.item("step", step)
        observation_id: str = identifier(request["observation_id"], "comparison observation")
        if observation_id not in item.observations:
            raise InputError("比较缺少本例实际独立观测 ID")
        pointer: JsonValue = request["field"]
        if not isinstance(pointer, str) or any(part.replace("~1", "/").replace("~0", "~").lower() in {"success", "assertion", "passed", "verdict"} for part in pointer.split("/")):
            raise InputError("比较不能采用脚本自述成功/断言字段")
        operator: str = text(request["operator"], "comparison.operator")
        if operator not in {"eq", "ne", "gt", "ge", "lt", "le", "contains", "delta"}:
            raise InputError("未知独立比较规则")
        basis: JsonObject = object_value(request["basis"], "comparison.basis")
        keys_only(basis, {"kind", "value", "reference_id", "field", "factor", "reviewer", "statement", "semantic_review", "original_is_text_contains"},
                  "comparison.basis", {"kind", "reviewer", "statement", "semantic_review"})
        if basis["reviewer"] != "current_agent":
            raise InputError("原自然语言到比较必须由当前 Agent 审核，不假称机器语义证明")
        text(basis["statement"], "basis.statement", trim=False)
        text(basis["semantic_review"], "basis.semantic_review", trim=False)
        expected: JsonValue
        if basis["kind"] == "literal":
            if "value" not in basis or set(basis) & {"reference_id", "field", "factor"}:
                raise InputError("literal 独立预期依据结构非法")
            expected = basis["value"]
        elif basis["kind"] == "baseline":
            if "value" in basis or "reference_id" not in basis or "field" not in basis:
                raise InputError("配置/需求基线必须引用登记来源，而非实际输出自导预期")
            reference_id: str = identifier(basis["reference_id"], "baseline reference")
            registered: JsonObject | None = self.state.references.get(reference_id)
            if registered is None:
                raise InputError("独立配置/需求基线尚未登记")
            origin: JsonObject = object_value(registered["origin"], "baseline origin")
            snapshot: JsonObject = object_value(origin["snapshot"], "baseline snapshot")
            baseline: JsonValue = strict_json(self.journal.verify_ref(snapshot), self.journal.limits.input_bytes, bom=True)
            field: JsonValue = basis["field"]
            if not isinstance(field, str):
                raise InputError("基线字段必须为 JSON Pointer")
            expected = field_value(baseline, field)
            factor: JsonValue = basis.get("factor", 1)
            if type(factor) is not int or factor not in {-1, 1}:
                raise InputError("基线 factor 仅允许明确的正负方向")
            if factor == -1:
                if type(expected) not in (int, float):
                    raise InputError("基线正负方向只适用于数值")
                expected = -cast(int | float, expected)
        else:
            raise InputError("预期依据只能为原文 literal 或独立配置/需求 baseline")
        scalar(expected)
        if operator == "contains" and basis.get("original_is_text_contains") is not True:
            raise InputError("contains 必须明确审核原预期确实是文本包含，弱断言将展示在报告")
        if operator == "delta" and "before" not in request:
            raise InputError("delta 缺少本例独立 before")
        if operator != "delta" and "before" in request:
            raise InputError("非 delta 比较不能混入 before")
        return {**request, "step_indices": indexes}, expected

    # 功能：执行独立业务比较并保留有效反例；参数 request 不采用动作回执成功作为断言。
    def _compare(self, request: JsonObject) -> JsonObject:
        self._active()
        case_id, original, item = self._current()
        binding, expected = self._binding(request, original, item)
        observation: JsonObject = item.observations[str(binding["observation_id"])]
        actual: JsonValue = None
        before_value: JsonValue = None
        computed: JsonValue = None
        matched: bool | None = None
        valid: bool = False
        diagnostic: str = ""
        try:
            if binding["scope"] == "expected" and item.completion_pending() is not None:
                raise InputError("业务完成条件尚未确认，当前观察不能用于最终结果断言")
            if observation.get("valid") is not True or observation.get("error") or self.target is None or observation.get("build_guid") != self.target.build_guid:
                raise InputError("本例独立观测缺目标/旧帧/异常，不能判定")
            if item.actions:
                action_id: str = item.actions[-1]
                action_frame: int = integer(record_data(self.state.results[action_id]).get("frame"), "action frame", 0)
                if observation.get("after_command_id") != action_id or integer(observation.get("frame"), "actual frame", 0) <= action_frame:
                    raise InputError("比较未使用本例最后动作后的独立新帧")
            actual = field_value(observation.get("value"), str(binding["field"]))
            if binding["operator"] == "delta":
                before_binding: JsonObject = object_value(binding.get("before"), "delta.before")
                keys_only(before_binding, {"observation_id", "field"}, "delta.before", {"observation_id", "field"})
                before_id: str = identifier(before_binding["observation_id"], "before observation")
                previous: JsonObject | None = item.observations.get(before_id)
                if previous is None or previous.get("valid") is not True or previous.get("target") != observation.get("target") or before_id == binding["observation_id"] or previous.get("build_guid") != observation.get("build_guid"):
                    raise InputError("delta before 不属于同例同目标有效独立观测")
                if integer(previous.get("frame"), "before frame", 0) >= integer(observation.get("frame"), "after frame", 0):
                    raise InputError("delta before/after 不存在独立新帧")
                if item.actions:
                    action = self.state.commands[item.actions[-1]]
                    if integer(previous.get("record_seq"), "before record") >= integer(action.get("seq"), "action record"):
                        raise InputError("delta before 不在动作之前")
                before_value = field_value(previous.get("value"), str(before_binding["field"]))
            basis: JsonObject = object_value(binding["basis"], "basis")
            matched, computed = compare_values(str(binding["operator"]), actual, expected, before_value,
                                               basis.get("original_is_text_contains") is True)
            valid = True
        except InputError as exc:
            diagnostic = str(exc)
        verdict: str = "passed" if valid and matched else "failed" if valid else "test_inconclusive"
        comparison: JsonObject = {
            "comparison_id": binding["comparison_id"], "binding": binding, "request_origin": self._request_origin,
            "actual_observation_id": binding["observation_id"], "actual_field": binding["field"],
            "actual": actual, "before_value": before_value, "expected_value": expected, "computed_value": computed,
            "valid": valid, "matched": matched, "status": verdict, "diagnostic": diagnostic,
            "semantic_equivalence": "current_agent_review_not_machine_proof",
            "assertion_strength": "text_contains_review_required" if binding["operator"] == "contains" else "strict_business_scalar",
        }
        reference: JsonObject = self.journal.store("comparison", canonical(comparison), {
            "kind": "host_comparison", "observation_id": binding["observation_id"],
            "binding_sha256": digest(canonical(binding)),
        }, case_id)
        self.journal.append("comparison", {**comparison, "evidence": reference}, case_id)
        self._refresh()
        return {**comparison, "evidence": reference}

    # 功能：写本例唯一真实四状态 final；参数 status 不能覆盖既有有效反例或把 partial 判通过。
    def _final(self, request: JsonObject, dry_run: bool = False) -> JsonObject:
        keys_only(request, {"status", "reason", "category", "required_permission"}, "final", {"status"})
        self._active()
        case_id, original, item = self._current()
        if case_id == CONTROL_CASE and not dry_run:
            raise InputError("共享准备必须使用 chain-end，不能产生业务用例 final")
        status: str = text(request["status"], "final.status")
        if status not in VERDICTS:
            raise InputError("final 只允许 passed/failed/blocked/test_inconclusive")
        coverage: JsonObject = case_coverage(original, item)
        reason: str = str(request.get("reason", ""))
        effective: str = status
        if item.failed_comparisons:
            effective = "failed"
            reason = reason or "本例存在有效业务反例；不因未归因/环境/请求状态改变失败"
        elif status == "failed":
            raise InputError("缺少有效业务反例，不能虚构产品 failed")
        elif status == "passed" and self.state.frozen:
            raise InputError("本轮已冻结或存在未知阶段，不能凭早先覆盖结果声明本例 passed")
        elif status == "passed" and item.frozen:
            raise InputError("本例已因脚本自身缺陷冻结；不能声明 passed")
        elif status == "passed" and coverage["all_matched"] is not True:
            raise InputError("原步骤/预期/前置覆盖不足或观测无效，partial 不得 passed")
        elif status == "blocked":
            category: str = text(request.get("category"), "block category")
            if category == "permission":
                permission: str = text(request.get("required_permission"), "required_permission")
                if self.target is None or permission in self.target.permissions or permission not in PERMISSIONS:
                    raise InputError("权限阻塞必须引用明确缺少的已知权限")
            elif category == "environment":
                if not any(record["event"] == "environment_blocked" for record in self.journal.records):
                    raise InputError("环境 blocked 缺少本轮真实环境阻断记录")
            elif category == "critical_precondition":
                if not any(comparison.get("valid") is True and comparison.get("matched") is False and object_value(comparison["binding"], "binding").get("scope") == "precondition" for comparison in item.comparisons.values()):
                    raise InputError("关键前置 blocked 缺少独立未满足事实")
            elif category != "user_stop":
                raise InputError("blocked 需要明确环境/权限/关键前置/用户停止来源")
        elif status == "test_inconclusive":
            inconclusive: str = text(request.get("category"), "inconclusive category")
            if inconclusive == "not_attempted":
                raise InputError("本例尚未执行任何动作/读取；不确定只能来自真实尝试")
            elif inconclusive == "insufficient_observation":
                # 旧帧/编译失败/字段缺失都属于真实观测后的「不足」，判据是有没有真的读过，而不是读得是否完美。
                # 本例因脚本自身缺陷冻结时，已有真实下发命令与未知回执，同样属「读过但不足」。
                if not item.observations and not item.frozen:
                    raise InputError("观测不足必须已有关联的本轮观测或本例真实脚本失败记录；从未观测不得判不确定")
            elif inconclusive == "not_constructible":
                attempted: bool = bool(item.actions) or any(record["event"] == "environment_blocked" for record in self.journal.records)
                if not attempted:
                    raise InputError("不可构造必须已有一次真实构造尝试（动作或环境阻断记录）")
                text(reason, "not_constructible.reason", trim=False)
            else:
                raise InputError("test_inconclusive 需要明确 category：insufficient_observation/not_constructible/not_attempted")
        if effective != "passed":
            text(reason, "non-passed.reason", trim=False)
        final: JsonObject = {"status": effective, "requested_status": status,
                             "reason": reason or "本例所有原步骤、前置及原预期均有有效独立关联",
                             "category": request.get("category"), "coverage": coverage,
                             "required_permission": request.get("required_permission"),
                             "comparison_ids": list(item.comparisons), "observation_ids": list(item.observations),
                             "action_command_ids": list(item.actions), "group_id": item.group_id,
                             "start_seq": item.started["seq"], "start_hash": item.started["hash"],
                              "request_origin": self._request_origin}
        if dry_run:
            return final
        reference: JsonObject = self.journal.store("final", canonical(final), {"kind": "case_final", "case_id": case_id}, case_id)
        record: JsonObject = self.journal.append("case_final", {**final, "evidence": reference}, case_id)
        self._refresh()
        return {"case_id": case_id, **final, "evidence": reference, "final_seq": record["seq"]}

    # 功能：登记独立配置/需求基线，保留原字节及不可变来源；参数 path 指向明确 JSON。
    def _baseline(self, request: JsonObject) -> JsonObject:
        keys_only(request, {"reference_id", "kind", "path", "sha256", "review"}, "baseline",
                  {"reference_id", "kind", "path", "sha256", "review"})
        self._active()
        reference_id: str = identifier(request["reference_id"], "reference_id")
        if reference_id in self.state.references or request["kind"] not in {"configuration", "requirements"}:
            raise InputError("独立基线重复或类别不明")
        text(request["review"], "baseline.review", trim=False)
        path: Path = local_path(text(request["path"], "baseline.path"), self._request_base)
        raw: bytes = read_regular(path, self.journal.limits.input_bytes)
        if digest(raw) != hash_value(request["sha256"], "baseline.sha256"):
            raise IntegrityError("独立基线原字节摘要不匹配")
        SecretGuard().check(strict_json(raw, self.journal.limits.input_bytes, bom=True))
        origin: JsonObject = self.journal.origin(path, raw, "baseline")
        registered: JsonObject = {"reference_id": reference_id, "kind": request["kind"], "review": request["review"],
                                  "origin": origin, "request_origin": self._request_origin}
        self.journal.append("baseline_registered", registered)
        self._refresh()
        return registered

    # 功能：实时记录归因，产品问题必须关联有效反例；参数分类不修改 final。
    def _attribute(self, request: JsonObject) -> JsonObject:
        keys_only(request, {"case_id", "classification", "issue_id", "description", "root_cause", "verification", "comparison_ids", "observation_ids"},
                  "attribute", {"case_id", "classification", "description", "verification", "comparison_ids", "observation_ids"})
        self._active()
        case_id: str = text(request["case_id"], "attribution.case_id")
        item: CaseState | None = self.state.cases.get(case_id)
        if item is None:
            raise InputError("归因缺少本轮原用例")
        classification: str = text(request["classification"], "classification")
        if classification not in {"product_confirmed", "unattributed_failure", "locator_error", "environment_blocked", "condition_not_constructible", "tool_error"}:
            raise InputError("归因类别不在固定口径内")
        comparisons: JsonValue = request["comparison_ids"]
        observations: JsonValue = request["observation_ids"]
        if not isinstance(comparisons, list) or not isinstance(observations, list):
            raise InputError("归因必须列实际本例比较/观测 ID")
        for value in comparisons:
            if identifier(value, "attribution comparison") not in item.comparisons:
                raise InputError("归因引用了不存在的本例比较")
        for value in observations:
            if identifier(value, "attribution observation") not in item.observations:
                raise InputError("归因引用了不存在的本例观测")
        text(request["description"], "attribution.description", trim=False)
        text(request["verification"], "attribution.verification", trim=False)
        if classification in {"product_confirmed", "unattributed_failure"} and not set(str(value) for value in comparisons) & set(item.failed_comparisons):
            raise InputError("产品问题/未归因失败必须关联本例有效反例，不以动作回执计 Bug")
        issue_id: str | None = None
        if classification == "product_confirmed":
            text(request.get("root_cause"), "root_cause", trim=False)
            issue_id = identifier(request.get("issue_id", new_id("issue")), "issue_id")
            if any(record_data(record).get("issue_id") == issue_id for record in self.journal.records if record["event"] == "attribution"):
                raise InputError("issue_id 重复")
        elif request.get("issue_id") is not None:
            raise InputError("仅已确认产品问题能登记 issue_id")
        attribution: JsonObject = {**request, "issue_id": issue_id, "request_origin": self._request_origin,
                                   "product_status_unchanged": True, "fix_executed": False}
        reference: JsonObject = self.journal.store("attribution", canonical(attribution), {
            "kind": "case_attribution", "comparison_ids": comparisons, "observation_ids": observations,
        }, case_id)
        self.journal.append("attribution", {**attribution, "evidence": reference}, case_id)
        return {**attribution, "evidence": reference}

    # 功能：沉淀本轮已验证定位事实，不冒充原行为通过；参数仅接受有效观察及独立通过比较。
    def _reference(self, request: JsonObject) -> JsonObject:
        keys_only(request, {"case_id", "description", "target", "observation_ids", "comparison_ids", "source_lookup"},
                  "reference", {"case_id", "description", "target", "observation_ids", "comparison_ids"})
        self._active()
        case_id: str = text(request["case_id"], "reference.case_id")
        item: CaseState | None = self.state.cases.get(case_id)
        if item is None:
            raise InputError("运行时参考缺少本例事实")
        observations: JsonValue = request["observation_ids"]
        comparisons: JsonValue = request["comparison_ids"]
        if not isinstance(observations, list) or not observations or not isinstance(comparisons, list) or not comparisons:
            raise InputError("运行时参考必须有真实观察和独立验证")
        for value in observations:
            observation: JsonObject | None = item.observations.get(identifier(value, "reference observation"))
            if observation is None or observation.get("valid") is not True or observation.get("target") != request["target"]:
                raise InputError("参考定位目标未在当前实例独立验证")
        for value in comparisons:
            comparison: JsonObject | None = item.comparisons.get(identifier(value, "reference comparison"))
            if comparison is None or comparison.get("valid") is not True or comparison.get("matched") is not True:
                raise InputError("候选/失败/动作回执不能作为已验证参考")
        text(request["description"], "reference.description", trim=False)
        fact: JsonObject = {**request, "build_guid": self.target.build_guid if self.target is not None else None,
                            "request_origin": self._request_origin, "scope": "verified_runtime_fact_only"}
        reference: JsonObject = self.journal.store("runtime_reference", canonical(fact), {"kind": "verified_reference"}, case_id)
        self.journal.append("reference_recorded", {**fact, "evidence": reference}, case_id)
        return {**fact, "evidence": reference}

    # 功能：从实际桥接观测导入有界日志/截图，核验路径/大小/摘要/归属；参数不接受任意附件替代观察。
    def _collect_evidence(self, request: JsonObject) -> JsonObject:
        keys_only(request, {"observation_id", "field", "privacy_review"}, "collect-evidence", {"observation_id", "field", "privacy_review"})
        self._active()
        case_id, original, item = self._current()
        observation_id: str = identifier(request["observation_id"], "artifact observation")
        observation: JsonObject | None = item.observations.get(observation_id)
        if observation is None or observation.get("valid") is not True or self.target is None:
            raise InputError("附件来源必须为当前本例有效实际观测")
        pointer: JsonValue = request["field"]
        if not isinstance(pointer, str):
            raise InputError("附件元数据字段必须为 JSON Pointer")
        review: JsonObject = object_value(request["privacy_review"], "artifact privacy review")
        keys_only(review, {"reviewer", "statement"}, "artifact privacy review", {"reviewer", "statement"})
        if review["reviewer"] != "current_agent":
            raise InputError("日志/截图收取必须由当前 Agent 做敏感审查，不声称自动视觉脱敏")
        text(review["statement"], "privacy review statement", trim=False)
        metadata: JsonObject = object_value(field_value(observation.get("value"), pointer), "artifact metadata")
        metadata_fields: set[str] = {"path", "sha256", "bytes", "kind", "run_id", "case_id", "command_id", "build_guid", "frame", "privacy"}
        keys_only(metadata, metadata_fields, "artifact metadata", metadata_fields)
        if metadata["run_id"] != self.journal.run_id or metadata["case_id"] != case_id or metadata["command_id"] != observation["command_id"] or metadata["build_guid"] != self.target.build_guid or integer(metadata["frame"], "artifact frame", 0) != observation["frame"]:
            raise IntegrityError("附件不属于本轮/本例/本次实际观察帧/构建")
        if metadata["privacy"] != "public_reviewed":
            raise IntegrityError("附件敏感状态未知或未审核，拒绝收取")
        kind: str = text(metadata["kind"], "artifact kind")
        permission: str = "screenshot" if kind == "screenshot" else "log_read" if kind == "log" else ""
        if not permission or permission not in self.target.permissions:
            raise EnvironmentBlocked("附件类别未获独立截图/日志读取许可")
        path: Path = local_path(text(metadata["path"], "artifact path"), Path.cwd())
        if not any(path.is_relative_to(root) for root in self.target.evidence_roots):
            raise InputError("实际附件不在明确授权的 evidence_roots 中")
        content: bytes = read_regular(path, self.target.limits.evidence_bytes)
        if len(content) != integer(metadata["bytes"], "artifact bytes", 1, self.target.limits.evidence_bytes) or digest(content) != hash_value(metadata["sha256"], "artifact digest"):
            raise IntegrityError("实际附件来源字节/大小/摘要不匹配")
        if kind == "screenshot" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise InputError("截图实际字节不是 PNG")
        reference: JsonObject = self.journal.store("artifact", content, {
            "kind": "observed_artifact", "observation_id": observation_id, "field": pointer,
            "original_path": str(path), "original_sha256": digest(content), "artifact_kind": kind,
            "build_guid": observation["build_guid"], "frame": observation["frame"], "privacy_review": review,
        }, case_id, ".png" if kind == "screenshot" else ".log")
        self.journal.append("artifact_collected", {"observation_id": observation_id, "field": pointer,
                                                  "evidence": reference, "request_origin": self._request_origin,
                                                  "privacy_review": review}, case_id)
        return reference

    # 功能：记录具体计时/源码查询/阻塞/污染说明，不回填时钟；参数 related_seq 为精确本轮事件位置。
    def _note(self, request: JsonObject) -> JsonObject:
        keys_only(request, {"case_id", "category", "message", "related_seq"}, "note", {"category", "message", "related_seq"})
        self._active()
        if request["category"] not in {"gap_explanation", "overrun_reason", "source_lookup", "blockage", "rollback_risk"}:
            raise InputError("note 类别非法")
        seq: int = integer(request["related_seq"], "related_seq", 1, len(self.journal.records))
        text(request["message"], "note.message", trim=False)
        case_id: JsonValue = request.get("case_id", self.state.current)
        if case_id is not None and (not isinstance(case_id, str) or case_id not in self.state.cases):
            raise InputError("note 不属于本轮用例")
        self.journal.append("case_note", {**request, "related_hash": self.journal.records[seq - 1]["hash"],
                                           "request_origin": self._request_origin}, cast(str | None, case_id))
        return {"noted": True, "related_seq": seq}

    # 功能：先全集审计再明确收口/计时；参数 interrupted_reason 为空时拒绝不完整全集。
    def _close(self, request: JsonObject) -> JsonObject:
        keys_only(request, {"interrupted_reason"}, "close")
        self._active()
        if self.cases is None:
            raise IntegrityError("完整原用例未加载")
        missing: list[str] = [case.case_id for case in self.cases.cases if case.case_id not in self.state.cases or self.state.cases[case.case_id].final is None]
        interrupted: JsonValue = request.get("interrupted_reason")
        if missing and (not isinstance(interrupted, str) or not interrupted.strip()):
            raise InputError("全集尚未完成；拒绝完整 close，必须明确中断原因，缺例不会被补假结果")
        if interrupted is not None:
            text(interrupted, "interrupted_reason", trim=False)
        from .report import audit_run
        audit: JsonObject = audit_run(self, require_closed=False)
        audit_record: JsonObject = self.journal.append("audit_complete", {"audit": audit, "head_before": self.journal.records[-1]["hash"]})
        closed: JsonObject = self.journal.append("session_closed", {"complete": not missing,
                                                                  "missing_case_ids": missing, "unfinished_case": self.state.current,
                                                                  "interrupted_reason": interrupted, "frozen": self.state.frozen,
                                                                  "audit_seq": audit_record["seq"], "audit_hash": audit_record["hash"],
                                                                  "process_cleanup": "disconnect_only_no_process_operation"})
        initial: JsonObject = record_data(self.journal.records[0])
        self.journal.finish_timing(self.journal.records[0], "child" if initial.get("parent") or initial.get("workflow") else "self")
        self._refresh()
        return {"closed": True, "complete": not missing, "missing_case_ids": missing,
                "close_seq": closed["seq"], "interrupted_reason": interrupted}


    # 功能：外部来源失效时仅核验私有快照、记录中断并闭合 writer；参数必须有明确中断原因，绝不产正式报告或假 final。
    def _close_integrity(self, request: JsonObject) -> JsonObject:
        keys_only(request, {"interrupted_reason"}, "integrity close", {"interrupted_reason"})
        self._active()
        reason: str = text(request["interrupted_reason"], "interrupted_reason", trim=False)
        if self.cases is None or not self.state.frozen or self._source_integrity_valid:
            raise IntegrityError("本地来源中断缺少原快照或唯一冻结状态")
        self.verify_sources(local_terminal=True)
        missing: list[str] = [case.case_id for case in self.cases.cases if case.case_id not in self.state.cases or self.state.cases[case.case_id].final is None]
        diagnostic: JsonObject = {"run_id": self.journal.run_id, "interrupted_reason": reason,
            "missing_case_ids": missing, "historical_final_statuses": {
                case_id: record_data(item.final)["status"] for case_id, item in self.state.cases.items() if item.final is not None},
            "source_integrity_valid": False, "formal_report_eligible": False, "upload": "not_executed",
            "execution_terminated": False, "snapshot_only": True}
        body: bytes = ("# FunctionTest 中断诊断摘要\n\n<!-- 创建时间：" + str(self.journal.records[-1]["time_utc"]) +
                       "；作者：Cyou；功能：已验证本地快照的来源失效收尾；参数：本轮实际中断记录，不操作 Player。 -->\n\n"
                       "本文件不是正式测试报告，不能转换统计 JSON 或上传；没有补写任何用例 final。\n\n```json\n" +
                       canonical(diagnostic).decode("utf-8") + "\n```\n\n冻结不等于 Player 中的代码已终止；禁止恢复、重放或换根绕过。\n").encode("utf-8")
        write_new(self.journal.root / INTERRUPTION_SUMMARY_NAME, body)
        reference: JsonObject = {"evidence_id": new_id("ev"), "path": INTERRUPTION_SUMMARY_NAME,
            "sha256": digest(body), "bytes": len(body), "kind": "interruption_summary", "case_id": None,
            "source": {"kind": "local_source_integrity_interruption", "run_id": self.journal.run_id}}
        self.journal.verify_ref(reference)
        self.journal.append("source_integrity_interrupted", {"reason": reason, "snapshot_only": True,
            "formal_report_eligible": False, "execution_terminated": False, "evidence": reference})
        audit_record: JsonObject = self.journal.append("audit_complete", {"audit": {"valid": False,
            "source_integrity_valid": False, "formal_eligible": False, "missing_case_ids": missing,
            "scope": "private_snapshots_only_not_business_audit"}, "head_before": self.journal.records[-1]["hash"]})
        closed: JsonObject = self.journal.append("session_closed", {"complete": False,
            "missing_case_ids": missing, "unfinished_case": self.state.current, "interrupted_reason": reason,
            "frozen": True, "audit_seq": audit_record["seq"], "audit_hash": audit_record["hash"],
            "process_cleanup": "disconnect_only_no_process_operation"})
        initial: JsonObject = record_data(self.journal.records[0])
        self.journal.finish_timing(self.journal.records[0], "child" if initial.get("parent") or initial.get("workflow") else "self")
        self._refresh()
        return {"closed": True, "complete": False, "missing_case_ids": missing, "close_seq": closed["seq"],
                "interrupted_reason": reason, "source_integrity_valid": False, "formal_report_eligible": False,
                "interruption_summary": INTERRUPTION_SUMMARY_NAME, "upload": "not_executed"}

    # 功能：离线审计，不接触 Player；参数空对象，正式报告另要求计时闭合。
    def _audit(self, request: JsonObject) -> JsonObject:
        keys_only(request, set(), "audit")
        from .report import audit_run
        result: JsonObject = audit_run(self, require_closed=self.state.closed is not None)
        self.journal.append("audit_complete", {"audit": result, "head_before": self.journal.records[-1]["hash"]})
        return result

    # 功能：只调用包内唯一固定报告渲染；参数空对象，父拥有者会拒绝子报告。
    def _report(self, request: JsonObject) -> JsonObject:
        keys_only(request, set(), "report")
        from .report import render_run
        return render_run(self)


# 功能：初始化由相同 writer 计时的父上下文；参数 root 为明确新目录，不接受手填时间。
def initialize_parent(output_root: Path) -> Path:
    root: Path = local_path(str(output_root), Path.cwd(), missing_leaf=True)
    root.mkdir(parents=True, exist_ok=True)
    parent_id: str = new_id("parent")
    parent_root: Path = root / parent_id
    journal: Journal = Journal.create(parent_root)
    with journal:
        journal.append("parent_init", {"report_owner": "parent", "children": [], "upload": "not_executed"}, run_id=parent_id)
        journal.append("cli_result", {"operation": "context-init", "call_id": new_id("call"), "ok": True,
                                      "result": {"root": str(parent_root), "invocation_id": parent_id, "report_owner": "parent"}})
    return parent_root


# 功能：父上下文在所有子收口/审计之后闭合；参数 root 不能覆盖父/子既有正式报告。
def close_parent(root: Path) -> JsonObject:
    from .evidence import local_cli_call
    with Journal(root) as journal, local_cli_call(journal, "context-close") as response:
        if not journal.records or journal.records[0]["event"] != "parent_init" or any(record["event"] in {"parent_closed", "report_intent"} for record in journal.records):
            raise InputError("父上下文不是未关闭且未渲染的包内 writer 上下文")
        children: list[JsonObject] = [record_data(record) for record in journal.records if record["event"] == "child_registered"]
        if not children:
            raise InputError("父上下文没有完整登记的子会话")
        summaries: list[JsonObject] = []
        formal_eligible: bool = True
        from .report import audit_interruption, audit_run, child_audit_summary
        for child in children:
            with Session(Path(str(child["root"]))) as session:
                if session.journal.run_id != child["run_id"] or session.journal.records[0]["hash"] != child["init_hash"]:
                    raise IntegrityError("父/子初始化身份不匹配")
                parent: JsonObject = object_value(record_data(session.journal.records[0]).get("parent"), "child parent")
                if parent.get("root") != str(journal.root.absolute()) or parent.get("invocation_id") != journal.run_id or parent.get("init_hash") != journal.records[0]["hash"]:
                    raise IntegrityError("子会话不属于当前唯一包内父")
                if session.state.integrity_interrupted:
                    summary: JsonObject = audit_interruption(session)
                    formal_eligible = False
                else:
                    summary = child_audit_summary(audit_run(session, require_closed=True))
                if session.state.report is not None:
                    raise IntegrityError("子会话已经渲染正式报告，父不能重复渲染")
                summaries.append({"run_id": child["run_id"], "audit": summary, "timing_hash": session.state.timing["hash"] if session.state.timing else None})
        journal.append("parent_audit_complete", {"children": summaries})
        journal.append("parent_closed", {"children": [child["run_id"] for child in children]})
        journal.finish_timing(journal.records[0], "parent")
        result: JsonObject = {"closed": True, "child_count": len(children), "invocation_id": journal.run_id,
                              "formal_report_eligible": formal_eligible}
        response["result"] = result
        return result
