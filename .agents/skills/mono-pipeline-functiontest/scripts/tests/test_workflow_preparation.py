"""创建日期：2026-10-27；作者：Cyou。
功能：原始材料/内部准备产物责任、未批准默认值及全量来源守卫的离线回归。
参数：真实 Skill 文档/模板与临时两例来源；不连接 Player，不证明模型语义整理已成功。
"""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from typing import cast

from ..contracts import InputError, JsonObject, Limits, canonical, digest, strict_json
from ..inputs import CaseInput, parse_cases, parse_provenance

SKILL_ROOT: Path = Path(__file__).resolve().parents[2]


class WorkflowPreparationTests(unittest.TestCase):
    """离线输入兼容与工作流契约；夹具不是实际游戏或已批准目标。"""

    # 功能：创建两例原文与完整内部输入；参数 root 为本例独有临时目录。
    def prepared_inputs(self, root: Path) -> tuple[CaseInput, JsonObject, Path]:
        source: Path = root / "original-cases.md"
        source.write_text(
            "<!-- 创建日期：2026-10-27；作者：Cyou；功能：不可执行的两例来源夹具。 -->\n"
            "# SOURCE-1\n前置：初始状态\n步骤 1：查看标题\n预期 1：显示原始标题\n附加字段：优先级高\n"
            "# SOURCE-2\n前置：初始状态\n步骤 2：查看说明\n预期 2：显示原始说明\n附加字段：优先级低\n",
            encoding="utf-8",
        )
        document: JsonObject = {
            "_comment": "内部整理夹具，不证明自然语言语义等价，不作为实际测试用例。",
            "cases": [
                {"case_id": "SOURCE-1", "title": "标题原例", "preconditions": ["初始状态"],
                 "steps": [{"index": 1, "text": "查看标题", "original_note": "保留步骤字段"}],
                 "expected": [{"index": 1, "text": "显示原始标题"}], "priority": "高"},
                {"case_id": "SOURCE-2", "title": "说明原例", "preconditions": ["初始状态"],
                 "steps": [{"index": 2, "text": "查看说明"}],
                 "expected": [{"index": 2, "text": "显示原始说明"}], "priority": "低"},
            ],
        }
        original: CaseInput = parse_cases(canonical(document))
        provenance: JsonObject = {
            "schema": "mono-pipeline-provenance/1",
            "sources": [{"path": str(source), "sha256": digest(source.read_bytes())}],
            "review": {"reviewer": "current_agent", "complete": True,
                       "case_ids": [case.case_id for case in original.cases],
                       "statement": "仅夹具：保留两例编号、索引、附加字段及完整来源，无 Player 操作。"},
        }
        return original, provenance, source

    # 功能：确认 Agent 整理结构可被原解析器使用且不删减；参数 self 为测试实例。
    def test_prepared_input_preserves_all_original_fields_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mpft-prepared-source-") as directory:
            original, provenance, source = self.prepared_inputs(Path(directory))
            self.assertEqual([case.case_id for case in original.cases], ["SOURCE-1", "SOURCE-2"])
            self.assertEqual(original.cases[0].raw["priority"], "高")
            self.assertEqual(original.cases[1].steps[0].index, 2)
            self.assertEqual(cast(JsonObject, original.cases[0].steps[0].original)["original_note"], "保留步骤字段")
            records: list[JsonObject] = parse_provenance(provenance, original, source.parent, Limits())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["sha256"], digest(source.read_bytes()))
            self.assertEqual(original.raw_sha256, digest(original.raw_bytes))

    # 功能：遗漏/重排原例不得以内部整理放行；参数 self 为测试实例。
    def test_prepared_provenance_rejects_missing_or_reordered_cases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mpft-prepared-coverage-") as directory:
            original, provenance, source = self.prepared_inputs(Path(directory))
            for identities in (["SOURCE-1"], ["SOURCE-2", "SOURCE-1"]):
                with self.subTest(case_ids=identities):
                    altered: JsonObject = copy.deepcopy(provenance)
                    cast(JsonObject, altered["review"])["case_ids"] = identities
                    with self.assertRaises(InputError):
                        parse_provenance(altered, original, source.parent, Limits())

    # 功能：原来源字节变化仍被拒绝；参数 self 为测试实例。
    def test_prepared_provenance_rejects_source_tampering(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mpft-prepared-tamper-") as directory:
            original, provenance, source = self.prepared_inputs(Path(directory))
            source.write_text(source.read_text(encoding="utf-8") + "原来源被修改\n", encoding="utf-8")
            with self.assertRaisesRegex(InputError, "整理来源原字节摘要不匹配"):
                parse_provenance(provenance, original, source.parent, Limits())

    # 功能：内部结构拥有者明确且保留未批准默认值；参数 self 为测试实例。
    def test_templates_are_agent_owned_and_remain_unapproved(self) -> None:
        for name in ("cases.json", "provenance.json", "package-approval.json", "target-permission.json"):
            with self.subTest(template=name):
                document: JsonObject = cast(JsonObject, strict_json(
                    (SKILL_ROOT / "assets/templates" / name).read_bytes(), Limits().input_bytes))
                self.assertIn("由当前 Agent", str(document["_comment"]))
                self.assertIn("不要求用户手写", str(document["_comment"]))
                if name == "provenance.json":
                    self.assertIs(cast(JsonObject, document["review"])["complete"], False)
                elif name == "package-approval.json":
                    self.assertIs(document["accepted"], False)
                    self.assertIs(document["complete_game_delivery"], False)
                elif name == "target-permission.json":
                    self.assertIs(cast(JsonObject, document["license"])["accepted"], False)
                    self.assertEqual(document["permissions"], [])
                    self.assertEqual(document["pid"], 0)

    # 功能：用户责任先于底层准备/现场动作，并明确禁止文件参数转交；参数 self 为测试实例。
    def test_workflow_orders_raw_input_preparation_then_live_cases(self) -> None:
        text: str = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8-sig")
        stages: tuple[str, ...] = ("## 用户输入与 Agent 产物", "## 阶段 1：", "## 阶段 2：", "## 阶段 3：")
        positions: list[int] = [text.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("不要求用户手写 JSON 或配置", text)
        self.assertIn("不把底层 CLI 的文件参数转交用户", text)
        self.assertIn("原始用例", text)
        self.assertIn("禁止输出带占位符的建议答案", text)
        self.assertIn("不为“已生成中间文件”询问是否继续", text)

    # 功能：简化输入不弱化自主启动边界、显式许可和冻结门禁；参数 self 为测试实例。
    def test_workflow_preserves_manual_start_and_explicit_permission_gates(self) -> None:
        text: str = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8-sig")
        for requirement in ("不杀死、不重启", "由当前 Agent 自主启动 Player", "不再要求用户手动启动",
                            "不伪造 PID/描述符", "不自造许可证", "不等于运行或账号操作授权",
                            "不默认接受或扩大权限", "整轮冻结", "同一 ID 永不重放", "仅离线准备时",
                            "不生成冒充测试完成的正式报告"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)
