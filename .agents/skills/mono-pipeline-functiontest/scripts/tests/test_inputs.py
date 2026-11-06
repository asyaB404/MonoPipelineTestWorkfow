"""创建日期：2026-10-26；作者：Cyou。
功能：原字节/全集/原索引/整理来源/严格比较及敏感输入的隔离测试。
参数：标准库 unittest 与本包临时夹具；不读取真实游戏状态。
"""
from __future__ import annotations

import unittest
from pathlib import Path

from ..contracts import InputError, IntegrityError, JsonObject, JsonValue, Limits, SecretGuard, canonical, compare_values, digest, field_value, strict_json
from ..inputs import case_index, parse_cases, parse_provenance, parse_target
from .support import Fixture, counter_case


class InputTests(unittest.TestCase):
    # 功能：验证完整原字节/BOM/CRLF 摘要及所有业务字段；参数 self 为测试实例。
    def test_preserves_original_bytes_and_all_fields(self) -> None:
        raw: bytes = b'\xef\xbb\xbf{\r\n"cases":[{"case_id":"C-1","title":"test","preconditions":[],"steps":["s"],"expected":["e"],"extra":{"zero":0,"flag":false}}],"meta":{"unknown":[1,2]}}\r\n'
        result = parse_cases(raw)
        self.assertEqual(result.raw_bytes, raw)
        self.assertEqual(result.raw_sha256, digest(raw))
        self.assertEqual(result.cases[0].raw["extra"], {"zero": 0, "flag": False})
        self.assertEqual(result.document["meta"], {"unknown": [1, 2]})

    # 功能：验证单例原输入及完整 expected 字符串；参数 self 为测试实例。
    def test_single_case_and_expected_text(self) -> None:
        case: JsonObject = counter_case()
        case["expected"] = "完整预期\n不做自动语义拆分"
        result = parse_cases(canonical(case))
        self.assertEqual(result.cases[0].expected[0].text, case["expected"])
        self.assertEqual(len(result.cases[0].expected), 1)

    # 功能：验证显式非连续原索引及原条目字段；参数 self 为测试实例。
    def test_explicit_source_indexes_preserved(self) -> None:
        case: JsonObject = counter_case()
        case["steps"] = [{"index": 5, "text": "第五原步骤", "extra": "保留"}]
        case["expected"] = [{"index": 42, "text": "第四十二原预期", "basis_note": "保留"}]
        result = parse_cases(canonical([case]))
        self.assertEqual(result.cases[0].item("step", 5).original["extra"], "保留")
        self.assertEqual(result.cases[0].item("expected", 42).index, 42)
        self.assertEqual(case_index(result)["case_ids"], ["C-1"])

    # 功能：拒重复编号，包括大小写冲突；参数 self 为测试实例。
    def test_duplicate_case_ids_rejected(self) -> None:
        with self.assertRaises(InputError):
            parse_cases(canonical([counter_case("C-1"), counter_case("c-1")]))

    # 功能：拒重复原步骤/预期/前置索引；参数 self 为测试实例。
    def test_duplicate_source_indexes_rejected(self) -> None:
        for name in ("steps", "expected", "preconditions"):
            with self.subTest(field=name):
                case: JsonObject = counter_case()
                case[name] = [{"index": 2, "text": "a"}, {"index": 2, "text": "b"}]
                with self.assertRaises(InputError):
                    parse_cases(canonical([case]))

    # 功能：拒重复 JSON 键，不能覆盖原预期；参数 self 为测试实例。
    def test_duplicate_json_keys_rejected(self) -> None:
        with self.assertRaises(InputError):
            strict_json(b'{"expected":1,"expected":2}', 1024)
        with self.assertRaises(InputError):
            strict_json(b'{"nested":{"x":1,"x":2}}', 1024)

    # 功能：拒 NaN/Infinity/溢出浮点常量；参数 self 为测试实例。
    def test_nonfinite_json_rejected(self) -> None:
        for raw in (b'{"v":NaN}', b'{"v":Infinity}', b'{"v":-Infinity}', b'{"v":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(InputError):
                strict_json(raw, 1024)

    # 功能：拒不清晰的 cases 容器及不完整字段；参数 self 为测试实例。
    def test_ambiguous_or_incomplete_source_rejected(self) -> None:
        for value in ({"cases": [counter_case()], "case_id": "C-1"}, {"cases": []}, {"case_id": "C-1", "title": "missing"}):
            with self.subTest(value=value), self.assertRaises(InputError):
                parse_cases(canonical(value))

    # 功能：初始化原索引不产生动作/静态计划；参数 self 为测试实例。
    def test_input_has_no_prebuilt_action_mapping(self) -> None:
        result = parse_cases(canonical({"cases": [counter_case()], "original_meta": True}))
        index: JsonObject = case_index(result)
        self.assertNotIn("operations", index)
        self.assertNotIn("plan", index)
        self.assertNotIn("mapped_steps", index)
        self.assertEqual(result.document["original_meta"], True)

    # 功能：整理来源要求全量 case_ids 和实际原摘要；参数 self 为测试实例。
    def test_provenance_full_coverage_and_digest(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        document: JsonObject = {"schema": "mono-pipeline-provenance/1", "sources": [{"path": str(fixture.cases_file), "sha256": digest(fixture.cases_file.read_bytes())}],
                                "review": {"reviewer": "current_agent", "complete": True, "case_ids": ["C-1"], "statement": "全量整理保留"}}
        self.assertEqual(len(parse_provenance(document, fixture.original, fixture.root, Limits())), 1)
        document["review"]["case_ids"] = []
        with self.assertRaises(InputError):
            parse_provenance(document, fixture.original, fixture.root, Limits())

    # 功能：integrity_mode 只接受 full/identity_only，缺省回落到 full；参数 self 为测试实例。
    def test_integrity_mode_defaults_to_full_and_rejects_unknown(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        base: JsonObject = strict_json(fixture.target_file.read_bytes(), Limits().input_bytes)
        self.assertEqual(parse_target(base, fixture.root).integrity_mode, "full")
        base["integrity_mode"] = "identity_only"
        self.assertEqual(parse_target(base, fixture.root).integrity_mode, "identity_only")
        base["integrity_mode"] = "skip_all"
        with self.assertRaises(InputError):
            parse_target(base, fixture.root)

    # 功能：目标关键未知字段/凭据字段不被接受；参数 self 为测试实例。
    def test_unknown_target_field_and_credentials_rejected(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        target: JsonObject = strict_json(fixture.target_file.read_bytes(), Limits().input_bytes)
        target["bypass"] = True
        with self.assertRaises(InputError):
            parse_target(target, fixture.root)
        with self.assertRaises(IntegrityError):
            SecretGuard().check({"nested": {"password": "private-value"}})

    # 功能：eq/ne 严格区分 bool/int/float/str，不靠隐式转换通过；参数 self 为测试实例。
    def test_eq_ne_are_strictly_typed(self) -> None:
        for actual, expected in ((True, 1), (1, 1.0), ("1", 1), (False, 0)):
            for operator in ("eq", "ne"):
                with self.subTest(actual=actual, expected=expected, operator=operator), self.assertRaises(InputError):
                    compare_values(operator, actual, expected)

    # 功能：数值大小比较拒 bool；参数 self 为测试实例。
    def test_numeric_ordering_rejects_boolean(self) -> None:
        with self.assertRaises(InputError):
            compare_values("gt", True, 0)
        self.assertEqual(compare_values("ge", 2, 1)[0], True)

    # 功能：contains 只限显式原文本包含审核；参数 self 为测试实例。
    def test_contains_requires_original_text_review(self) -> None:
        with self.assertRaises(InputError):
            compare_values("contains", "level:3", "level:")
        self.assertTrue(compare_values("contains", "message contains X", "X", text_contains=True)[0])

    # 功能：delta 严格计算 before/after，不将 +2 判成 +1；参数 self 为测试实例。
    def test_delta_exact_negative_counterexample(self) -> None:
        self.assertEqual(compare_values("delta", 4, 1, 3), (True, 1))
        self.assertEqual(compare_values("delta", 5, 1, 3), (False, 2))
        with self.assertRaises(InputError):
            compare_values("delta", 4.0, 1, 3)

    # 功能：缺字段/null 不能转换为 false/0；参数 self 为测试实例。
    def test_missing_null_and_pointer_escape(self) -> None:
        with self.assertRaises(InputError):
            field_value({}, "/missing")
        with self.assertRaises(InputError):
            compare_values("eq", None, False)
        self.assertEqual(field_value({"a/b": {"~": 3}}, "/a~1b/~0"), 3)

    # 功能：JSON 深度/字节越界被拒绝；参数 self 为测试实例。
    def test_json_limits(self) -> None:
        with self.assertRaises(InputError):
            strict_json(b'[[[[0]]]]', 1024, Limits(json_depth=2))
        with self.assertRaises(InputError):
            strict_json(b'{"long":"12345"}', 3)
