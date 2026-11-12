"""Created: 2026-11-05; Author: Codex.
Purpose: compile and execute the actual generated visual observation in isolated UI stubs.
Parameters: existing Windows .NET compiler and temporary fixtures only; no Unity or Player.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import cast

from ..contracts import InputError, JsonObject, Limits, SecretGuard
from ..pipeline import wrap_script
from ..session import builtin_button_click, builtin_observation
from .support import Fixture

FIXTURE = r'''
// Created: 2026-11-05; Author: Codex. Isolated synthetic UI, not a game runtime.
using System;
using System.Collections.Generic;
using System.Web.Script.Serialization;
namespace UnityEngine {
    public class Object {
        public int instanceID;
        public virtual int GetInstanceID() { return instanceID == 0 ? GetHashCode() : instanceID; }
    }
    public static class Time { public static int frameCount = 23; }
    public static class Application { public static string buildGUID = "fixture-build-v1"; }
    public static class Debug { public static bool isDebugBuild = true; }
    public struct Scene {
        // Return the scene membership of this explicitly isolated fixture.
        public bool IsValid() { return true; }
    }
    public class Component : Object {
        public GameObject gameObject;
        public Transform transform { get { return gameObject.transform; } }
        public string name { get { return gameObject.name; } }
        // Forward a typed query to this fixture's owner; T is the requested component.
        public T GetComponent<T>() where T : class { return gameObject.GetComponent<T>(); }
        // Return this owner's components; T is the requested component type.
        public T[] GetComponents<T>() where T : class { return gameObject.GetComponents<T>(); }
        // Forward a subtree query; includeInactive is accepted by the generated interface.
        public T[] GetComponentsInChildren<T>(bool includeInactive) where T : class {
            return gameObject.GetComponentsInChildren<T>(includeInactive);
        }
        // Return the first requested descendant from this synthetic hierarchy.
        public T GetComponentInChildren<T>(bool includeInactive) where T : class {
            T[] components = GetComponentsInChildren<T>(includeInactive);
            return components.Length == 0 ? null : components[0];
        }
    }
    public class Transform : Component {
        public Transform parent;
        public readonly List<Transform> children = new List<Transform>();
        public int childCount { get { return children.Count; } }
        // Return the child at the requested index.
        public Transform GetChild(int index) { return children[index]; }
    }
    public class Behaviour : Component {
        public bool enabled = true;
        public bool isActiveAndEnabled { get { return enabled && gameObject.activeInHierarchy; } }
    }
    public class GameObject : Object {
        public string name;
        public bool activeInHierarchy = true;
        public Scene scene;
        public readonly Transform transform;
        private readonly List<Component> components = new List<Component>();
        // Create one scene node; nameValue is its exact scene name.
        public GameObject(string nameValue) {
            name = nameValue;
            transform = new Transform();
            Attach(transform);
        }
        // Find an exact active path within this isolated hierarchy; path is not a real scene.
        public static GameObject Find(string path) {
            if (Resources.root == null) { return null; }
            foreach (Transform candidate in Resources.root.GetComponentsInChildren<Transform>(true)) {
                if (candidate == null || candidate.gameObject == null || !candidate.gameObject.activeInHierarchy) { continue; }
                string actualPath = candidate.name;
                Transform parent = candidate.parent;
                while (parent != null) { actualPath = parent.name + "/" + actualPath; parent = parent.parent; }
                if (actualPath == path) { return candidate.gameObject; }
            }
            return null;
        }
        // Add a controlled component instance; component is owned only by this fixture.
        public void Attach(Component component) { component.gameObject = this; components.Add(component); }
        // Return a stable local identity, never an identity of a real Unity object.
        public override int GetInstanceID() { return base.GetInstanceID(); }
        // Query the first typed component; T is supplied by the generated observation.
        public T GetComponent<T>() where T : class {
            foreach (Component component in components) { if (component is T) { return component as T; } }
            return null;
        }
        // Query all typed components; T is supplied by the generated observation.
        public T[] GetComponents<T>() where T : class {
            List<T> result = new List<T>();
            foreach (Component component in components) { if (component is T) { result.Add(component as T); } }
            return result.ToArray();
        }
        // Traverse this synthetic subtree; includeInactive does not hide fixture nodes.
        public T[] GetComponentsInChildren<T>(bool includeInactive) where T : class {
            List<T> result = new List<T>(GetComponents<T>());
            foreach (Transform child in transform.children) {
                result.AddRange(child.gameObject.GetComponentsInChildren<T>(includeInactive));
            }
            return result.ToArray();
        }
    }
    public struct Color {
        public float r, g, b, a;
        // Assign the exact channel values supplied by the synthetic test.
        public Color(float red, float green, float blue, float alpha) { r = red; g = green; b = blue; a = alpha; }
    }
    public static class ColorUtility {
        // Format the fixture's exact zero/one RGB channels using the Unity API shape.
        public static string ToHtmlStringRGB(Color value) {
            return ((int)(value.r * 255)).ToString("X2") + ((int)(value.g * 255)).ToString("X2")
                + ((int)(value.b * 255)).ToString("X2");
        }
        // Include alpha so fully transparent values are not silently treated as opaque.
        public static string ToHtmlStringRGBA(Color value) {
            return ToHtmlStringRGB(value) + ((int)(value.a * 255)).ToString("X2");
        }
    }
    public class Sprite : Object { public string name; }
    public static class Resources {
        public static Transform root;
        // Expose only the synthetic root to the requested resource type T.
        public static T[] FindObjectsOfTypeAll<T>() where T : class {
            return root == null ? new T[0] : root.GetComponentsInChildren<T>(true);
        }
    }
}
namespace UnityEngine.UI {
    public class Text : UnityEngine.Component { public string text; public UnityEngine.Color color; }
    public class Image : UnityEngine.Component { public UnityEngine.Sprite sprite; public UnityEngine.Color color; }
    public class ClickEvent {
        public int calls;
        public void Invoke() { calls++; }
    }
    public class Button : UnityEngine.Behaviour {
        public bool interactable = true;
        public readonly ClickEvent onClick = new ClickEvent();
        public bool IsInteractable() { return interactable; }
    }
    public class Toggle : UnityEngine.Component { public bool isOn; }
}
public class GameButton : UnityEngine.Behaviour {
    public bool interactable { get; set; }
    public bool groupAllowed = true;
    public int calls;
    public bool IsInteractable() { return interactable && groupAllowed; }
    public void InvokeOnClickListener() { calls++; }
}
public class GameText : UnityEngine.Component {
    public bool broken;
    public string text { get { return "Title"; } }
    public UnityEngine.Color color {
        get { if (broken) { throw new InvalidOperationException("isolated getter failure"); }
              return new UnityEngine.Color(1, 0, 0, 1); }
    }
}
public class GameImage : UnityEngine.Component {
    public bool broken;
    public UnityEngine.Sprite sprite {
        get { if (broken) { throw new InvalidOperationException("isolated getter failure"); }
              return new UnityEngine.Sprite { name = "quality-frame" }; }
    }
    public UnityEngine.Color color {
        get { if (broken) { throw new InvalidOperationException("isolated getter failure"); }
              return new UnityEngine.Color(0, 1, 0, 0); }
    }
}
public static class VisualFixture {
    // Execute the exact generated observation body, without a replacement implementation.
    private static object Read() { /* GENERATED_OBSERVATION */ }
    // Build the requested fixture variant; args contains native/custom/unloaded/broken.
    public static int Main(string[] args) {
        UnityEngine.GameObject root = new UnityEngine.GameObject("Root");
        UnityEngine.Resources.root = root.transform;
        string mode = args[0];
        if (mode == "custom" || mode == "broken") {
            root.Attach(new GameText { broken = mode == "broken" });
            root.Attach(new GameImage { broken = mode == "broken" });
        } else {
            root.Attach(new UnityEngine.UI.Text { text = "Title", color = new UnityEngine.Color(1, 0, 0, 1) });
            root.Attach(new UnityEngine.UI.Image { color = new UnityEngine.Color(0, 1, 0, 0),
                sprite = mode == "unloaded" ? null : new UnityEngine.Sprite { name = "quality-frame" } });
        }
        Console.Write(new JavaScriptSerializer().Serialize(Read()));
        return 0;
    }
}
'''


# Locate an existing compiler; no installation or Unity initialization is permitted.
def fixture_compiler() -> Path:
    windows: str | None = os.environ.get("WINDIR")
    if os.name != "nt" or windows is None:
        raise unittest.SkipTest("Generated C# requires an existing Windows .NET compiler")
    candidates: list[Path] = []
    for framework in ("Framework64", "Framework"):
        candidates.extend(sorted((Path(windows) / "Microsoft.NET" / framework).glob("v4*/csc.exe")))
    if not candidates:
        raise unittest.SkipTest("No existing compiler; no installation attempted")
    return candidates[-1]


# Compile and run the actual generated C#; source and args are isolated synthetic inputs.
def compile_fixture(test: unittest.TestCase, compiler: Path, source_text: str, args: list[str]) -> JsonObject:
    with tempfile.TemporaryDirectory(prefix="mpft-generated-unit-") as temporary:
        root: Path = Path(temporary)
        source: Path = root / "GeneratedFixture.cs"
        executable: Path = root / "GeneratedFixture.exe"
        source.write_text(source_text, encoding="utf-8")
        compiled: subprocess.CompletedProcess[str] = subprocess.run(
            [str(compiler), "/nologo", "/utf8output", "/target:exe", "/reference:System.Web.Extensions.dll",
             "/out:" + str(executable), str(source)], cwd=root, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=30, check=False,
        )
        test.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
        result: subprocess.CompletedProcess[str] = subprocess.run(
            [str(executable), *args], cwd=root, capture_output=True, text=True, timeout=30, check=False,
        )
        test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return cast(JsonObject, json.loads(result.stdout))


class BuiltinVisualTests(unittest.TestCase):
    """Exercise real generated C# against controlled standard and custom components."""

    compiler: Path

    # Locate an already installed compiler; cls does not download or initialize Unity.
    @classmethod
    def setUpClass(cls) -> None:
        cls.compiler = fixture_compiler()

    # Compile and run one actual generated body; mode and operation select isolated inputs.
    def read_node(self, mode: str, operation: str = "subtree", options: JsonObject | None = None) -> JsonObject:
        body: str = builtin_observation(operation, {"root": "Root", **(options or {})}).decode("utf-8")
        document: JsonObject = compile_fixture(self, self.compiler, FIXTURE.replace("/* GENERATED_OBSERVATION */", body), [mode])
        nodes: list[JsonObject] = cast(list[JsonObject], document["nodes"])
        self.assertEqual(len(nodes), 1)
        return nodes[0]

    # Standard components must retain exact raw RGB, RGBA and Sprite.name values.
    def test_standard_text_and_image_expose_raw_visual_values(self) -> None:
        for operation in ("chain", "subtree"):
            with self.subTest(operation=operation):
                node: JsonObject = self.read_node("native", operation)
                self.assertEqual(node["text"], "Title")
                self.assertEqual(node["text_color_rgb"], "ff0000")
                self.assertEqual(node["text_color_rgba"], "ff0000ff")
                self.assertEqual(node["image_color_rgb"], "00ff00")
                self.assertEqual(node["image_color_rgba"], "00ff0000")
                self.assertEqual(node["sprite_name"], "quality-frame")
                self.assertTrue(node["active"])
                self.assertTrue({"success", "passed", "assertion", "verdict"}.isdisjoint(node))

    # Custom controls use their public properties without needing project type references.
    def test_custom_game_controls_expose_the_same_raw_values(self) -> None:
        node: JsonObject = self.read_node("custom")
        self.assertEqual(node["text_color_rgb"], "ff0000")
        self.assertEqual(node["text_color_rgba"], "ff0000ff")
        self.assertEqual(node["image_color_rgba"], "00ff0000")
        self.assertEqual(node["sprite_name"], "quality-frame")

    # A failed property read must not invent a white color, empty name or zero channel.
    def test_failed_custom_getters_do_not_produce_default_visual_values(self) -> None:
        node: JsonObject = self.read_node("broken")
        self.assertEqual(node["text"], "Title")
        for key in ("text_color_rgb", "text_color_rgba", "image_color_rgb", "image_color_rgba", "sprite_name"):
            self.assertNotIn(key, node)

    # A real native image with no loaded sprite is explicit null, not a placeholder name.
    def test_native_unloaded_sprite_is_explicit_null(self) -> None:
        node: JsonObject = self.read_node("unloaded")
        self.assertIn("sprite_name", node)
        self.assertIsNone(node["sprite_name"])
        self.assertEqual(node["image_color_rgba"], "00ff0000")

    # Codex: initial discovery must not evaluate or return any visual properties.
    def test_names_only_discovery_contains_only_paths_names_and_activation(self) -> None:
        node: JsonObject = self.read_node("broken", "chain", {"names_only": True})
        self.assertEqual(node, {"path": "Root", "name": "Root", "active": True})

    # Codex: compile the exact attach wrapper saved by Session, including its names-only discovery.
    def test_actual_attach_wrapper_compiles_and_projects_initial_discovery(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            result: JsonObject = session.invoke("attach", {})
            intent: JsonObject = cast(JsonObject, session.state.commands[str(result["probe_command_id"])]["data"])
            wrapper: str = session.journal.verify_ref(cast(JsonObject, intent["script_wrapper"])).decode("utf-8")
        document: JsonObject = compile_fixture(self, self.compiler, FIXTURE.replace("/* GENERATED_OBSERVATION */", wrapper), ["native"])
        actual: JsonObject = cast(JsonObject, document["value"])
        self.assertIsNone(document["value_error"])
        self.assertTrue(actual["development"])
        # This is a .NET stub process, so it must not claim to be a Mono Player.
        self.assertFalse(actual["mono"])
        self.assertEqual(cast(JsonObject, actual["discovery"])["nodes"], [{"path": "Root", "name": "Root", "active": True}])

    # Compile the shipped fixed-path template; mode selects active, hidden or absent login.
    def read_login_state(self, mode: str) -> JsonObject:
        body: str = (Path(__file__).resolve().parents[2] / "assets/templates/read-login-state.cs").read_text(encoding="utf-8")
        source: str = FIXTURE.split("public static class VisualFixture {")[0] + r'''
public static class LoginFixture {
    // Execute the actual shipped template, without a substitute success flag.
    private static object Read() { /* LOGIN_TEMPLATE */ }
    // Build a fixed synthetic login hierarchy; args selects page visibility only.
    public static int Main(string[] args) {
        UnityEngine.GameObject root = new UnityEngine.GameObject("GameEntry");
        UnityEngine.Resources.root = root.transform;
        UnityEngine.Transform parent = root.transform;
        foreach (string name in new string[] { "Builtin", "UI", "AdapterArea", "Canvas0" }) {
            UnityEngine.GameObject child = new UnityEngine.GameObject(name);
            child.transform.parent = parent;
            parent.children.Add(child.transform);
            parent = child.transform;
        }
        if (args[0] != "absent") {
            UnityEngine.GameObject page = new UnityEngine.GameObject("UI_LoginGame");
            page.activeInHierarchy = args[0] == "active";
            page.transform.parent = parent;
            parent.children.Add(page.transform);
        }
        Console.Write(new JavaScriptSerializer().Serialize(Read()));
        return 0;
    }
}
'''
        return compile_fixture(self, self.compiler, source.replace("/* LOGIN_TEMPLATE */", body), [mode])

    # An active login page remains unfinished even without protocol or main-page controls.
    def test_fixed_login_template_reads_only_page_and_frame(self) -> None:
        self.assertEqual(self.read_login_state("active"), {"login_page_state": "active_in_hierarchy", "frame": 23})

    # Hidden cached pages and removed pages both satisfy the user's visible-page contract.
    def test_fixed_login_template_treats_hidden_or_removed_page_as_absent(self) -> None:
        for mode in ("hidden", "absent"):
            with self.subTest(mode=mode):
                self.assertEqual(self.read_login_state(mode), {"login_page_state": "absent", "frame": 23})


class BuiltinMemberTests(unittest.TestCase):
    """Codex 2026-11-12: execute production reflection against isolated field/property shapes."""

    compiler: Path

    # Locate the installed compiler; cls never launches a game or installs dependencies.
    @classmethod
    def setUpClass(cls) -> None:
        cls.compiler = fixture_compiler()

    # Compile the real wrapped observation; options/mode select members and synthetic identities.
    def read_members(self, operation: str, options: JsonObject, mode: str = "field") -> JsonObject:
        body: bytes = builtin_observation(operation, options)
        wrapper: str = wrap_script(body, "run-members", "R-1", "members", Limits(), SecretGuard()).decode("utf-8")
        source: str = FIXTURE.split("public static class VisualFixture {")[0] + r'''
public enum FixtureState { Ready, Pending }
public class LogicBase {
    private int inherited = 7;
    private int ParentProperty { get { return 11; } }
}
public class FixtureLogic : LogicBase {
    public bool isUnlocked = true;
    public bool isClaimed { get { return false; } }
    public int Zero { get { return 0; } }
    public string Empty = null;
    public object Nested = null;
    public object Unsupported = new object();
    public Func<int> Callback = delegate { throw new Exception("must not invoke"); };
    public FixtureState State = FixtureState.Ready;
    public double NotFinite = double.NaN;
    public int Broken { get { throw new Exception("isolated getter failure"); } }
    public int WriteOnly { set { throw new Exception("must not set"); } }
    public int this[int index] { get { throw new Exception("must not index"); } }
    // Simulate value-equal business objects; other is deliberately not an identity check.
    public override bool Equals(object other) { return other is FixtureLogic; }
    // All synthetic objects share a value hash to expose unsafe deduplication.
    public override int GetHashCode() { return 1; }
}
public class BinderBase : UnityEngine.Component { public object UILogicInst; }
public class FieldBinder : BinderBase { }
public class PropertyBinder : UnityEngine.Component { public object UILogicInst { get; set; } }
public class Adapter {
    private object m_Instance;
    // Store the synthetic instance in the legacy adapter field.
    public Adapter(object instance) { m_Instance = instance; }
}
public class LegacyBinder : UnityEngine.Component {
    private object m_MonoInvocationAdapter;
    // Bind the synthetic instance through the old private adapter layout.
    public LegacyBinder(object instance) { m_MonoInvocationAdapter = new Adapter(instance); }
}
public class NativeLogic : UnityEngine.Component { public int Count = 4; }
public static class MemberFixture {
    // Run the actual production wrapper and serialize only its projected result.
    private static object Read() { /* MEMBER_BODY */ }
    // Construct a selected UI subtree, a sibling decoy and optional duplicate instances.
    public static int Main(string[] args) {
        string mode = args[0];
        UnityEngine.GameObject root = new UnityEngine.GameObject("Root");
        UnityEngine.Resources.root = root.transform;
        UnityEngine.GameObject ui = new UnityEngine.GameObject("UI");
        ui.transform.parent = root.transform; root.transform.children.Add(ui.transform);
        UnityEngine.GameObject decoy = new UnityEngine.GameObject("UIOther");
        decoy.transform.parent = root.transform; root.transform.children.Add(decoy.transform);
        decoy.Attach(new FieldBinder { UILogicInst = new FixtureLogic() });
        object logic = mode == "null" ? null : new FixtureLogic();
        if (mode == "property") { ui.Attach(new PropertyBinder { UILogicInst = logic }); }
        else if (mode == "legacy") { ui.Attach(new LegacyBinder(logic)); }
        else if (mode == "native") { ui.Attach(new NativeLogic()); }
        else if (mode != "missing") { ui.Attach(new FieldBinder { UILogicInst = logic }); }
        if (mode == "same" || mode == "multiple") {
            ui.Attach(new FieldBinder { UILogicInst = mode == "same" ? logic : new FixtureLogic() });
        }
        if (mode == "inactive") { ui.activeInHierarchy = false; }
        Console.Write(new JavaScriptSerializer().Serialize(Read()));
        return 0;
    }
}
'''
        result: JsonObject = compile_fixture(self, self.compiler, source.replace("/* MEMBER_BODY */", wrapper), [mode])
        self.assertIsNone(result["value_error"])
        return cast(JsonObject, result["value"])

    # Read one legacy-compatible value; field and mode identify the synthetic source.
    def read_logic(self, field: str, mode: str = "field") -> JsonObject:
        return self.read_members("logic_field", {"root": "Root/UI", "logic_type": "FixtureLogic", "field": field}, mode)

    # Fields, properties, private base members and genuine false/zero remain distinct from missing values.
    def test_logic_reads_fields_properties_and_inherited_members(self) -> None:
        for field, expected, kind in (("isUnlocked", True, "field"), ("isClaimed", False, "property"),
                                       ("Zero", 0, "property"), ("inherited", 7, "field"), ("ParentProperty", 11, "property")):
            with self.subTest(field=field):
                result: JsonObject = self.read_logic(field)
                self.assertEqual(result["value"], expected)
                self.assertEqual(result["member_kind"], kind)
                self.assertEqual(result["instance_count"], 1)
                self.assertTrue(result["found"])
                self.assertTrue(result["readable"])
                self.assertIsNone(result["error"])

    # Both the current public binding and older adapter layout resolve without a game assembly reference.
    def test_logic_supports_property_binding_legacy_adapter_and_native_component(self) -> None:
        for mode in ("property", "legacy"):
            with self.subTest(mode=mode):
                self.assertTrue(self.read_logic("isUnlocked", mode)["value"])
        native: JsonObject = self.read_members("logic_field", {"root": "Root/UI", "logic_type": "NativeLogic", "field": "Count"}, "native")
        self.assertEqual(native["value"], 4)
        probe: JsonObject = self.read_members("member_probe", {"root": "Root/UI", "component_type": "PropertyBinder",
            "members": ["UILogicInst.Zero"]}, "property")
        row: JsonObject = cast(list[JsonObject], probe["nodes"])[0]
        self.assertEqual(cast(dict[str, JsonObject], row["members"])["UILogicInst.Zero"]["value"], 0)

    # Value equality must not collapse distinct runtime instances; multiple bindings to one object may deduplicate.
    def test_logic_distinguishes_missing_duplicate_and_shared_instances(self) -> None:
        for mode, count, error in (("missing", 0, "instance_missing"), ("null", 0, "instance_missing"),
                                    ("multiple", 2, "instance_ambiguous"), ("same", 1, None)):
            with self.subTest(mode=mode):
                result: JsonObject = self.read_logic("isUnlocked", mode)
                self.assertEqual(result["instance_count"], count)
                self.assertEqual(result["error"], error)
                self.assertEqual(result["readable"], count == 1)
                if count != 1:
                    self.assertIsNone(result["value"])

    # A missing path/getter is explicit; present null, enums and false keep their actual meanings.
    def test_probe_projects_each_member_independently(self) -> None:
        paths: list[str] = ["UILogicInst." + name for name in (
            "isUnlocked", "isClaimed", "Zero", "Empty", "inherited", "ParentProperty", "Missing", "Broken",
            "WriteOnly", "Item", "Unsupported", "Callback", "NotFinite", "State", "Nested.Count")]
        result: JsonObject = self.read_members("member_probe", {"root": "Root/UI", "component_type": "BinderBase", "members": paths})
        self.assertEqual(result["instance_count"], 1)
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["truncated"])
        row: JsonObject = cast(list[JsonObject], result["nodes"])[0]
        self.assertEqual(row["path"], "Root/UI")
        self.assertEqual(row["component_type"], "FieldBinder")
        self.assertTrue(row["active"])
        self.assertIsInstance(row["instance_id"], int)
        members: dict[str, JsonObject] = cast(dict[str, JsonObject], row["members"])
        for name, value in (("isUnlocked", True), ("isClaimed", False), ("Zero", 0), ("Empty", None),
                             ("inherited", 7), ("ParentProperty", 11), ("State", "Ready")):
            with self.subTest(name=name):
                self.assertTrue(members["UILogicInst." + name]["readable"])
                self.assertEqual(members["UILogicInst." + name]["value"], value)
        for name, error, found in (("Missing", "member_missing", False), ("Broken", "member_read_failed", True),
                                    ("WriteOnly", "member_not_readable", True), ("Item", "member_not_readable", True),
                                    ("Unsupported", "unsupported_value_type", True), ("Callback", "unsupported_value_type", True),
                                    ("NotFinite", "non_finite_value", True), ("Nested.Count", "member_owner_missing", False)):
            with self.subTest(name=name):
                member: JsonObject = members["UILogicInst." + name]
                self.assertEqual(member["error"], error)
                self.assertEqual(member["found"], found)
                self.assertFalse(member["readable"])
                self.assertIsNone(member["value"])
        self.assertEqual(members["UILogicInst.Zero"]["value_type"], "System.Int32")
        self.assertEqual(members["UILogicInst.Broken"]["member_kind"], "property")
        self.assertEqual(members["UILogicInst.Nested.Count"]["failed_segment"], "Count")

    # Count/truncation represent actual matched instances; hidden cached UI is explicitly marked.
    def test_probe_counts_and_limits_without_default_empty_business_values(self) -> None:
        options: JsonObject = {"root": "Root/UI", "component_type": "BinderBase", "members": ["UILogicInst.Zero"], "max_nodes": 1}
        for mode, count, truncated in (("missing", 0, False), ("field", 1, False), ("multiple", 2, True)):
            with self.subTest(mode=mode):
                result: JsonObject = self.read_members("member_probe", options, mode)
                self.assertEqual(result["instance_count"], count)
                self.assertEqual(result["count"], min(count, 1))
                self.assertEqual(result["truncated"], truncated)
        inactive: JsonObject = self.read_members("member_probe", options, "inactive")
        self.assertFalse(cast(list[JsonObject], inactive["nodes"])[0]["active"])

    # Feed actual compiled observations into the host; missing values cannot become passes or product failures.
    def test_generated_member_values_preserve_host_verdict_boundaries(self) -> None:
        for field, valid, matched, status in (("Zero", True, True, "passed"), ("inherited", True, False, "failed"),
                                              ("Missing", False, None, "test_inconclusive")):
            with self.subTest(field=field):
                actual: JsonObject = self.read_logic(field)
                fixture: Fixture = Fixture(cases=[{"case_id": "R-1", "title": "读取业务数量", "preconditions": [],
                    "steps": ["读取业务数量"], "expected": ["业务数量为0"]}])
                self.addCleanup(fixture.cleanup)
                fixture.world.override_read = True
                fixture.world.returned_value = actual
                with fixture.session() as session:
                    session.invoke("attach", {})
                    session.invoke("start-case", {"case_id": "R-1"})
                    session.invoke("observe", {"command_id": "read-members", "observation_id": "members",
                        "builtin": "logic_field", "builtin_options": {"root": "Root/UI", "logic_type": "FixtureLogic", "field": field},
                        "scope": "step", "index": 1, "original_text": "读取业务数量", "purpose": "step", "covers_step": True,
                        "target": fixture.world.target, "read_only_review": "隔离编译原字段读取，无业务副作用", "reason": "验证实际读取与判定边界"})
                    result: JsonObject = session.invoke("compare", fixture.comparison("expected-zero", "members", "/value", 0, case_id="R-1"))
                    self.assertEqual(result["valid"], valid)
                    self.assertEqual(result["matched"], matched)
                    self.assertEqual(result["status"], status)
                    final: JsonObject = {"status": status}
                    if status != "passed":
                        final["reason"] = "真实反例" if valid else "成员缺失，不能证明数量为0"
                    if not valid:
                        final["category"] = "insufficient_observation"
                    self.assertEqual(session.invoke("final", final)["status"], status)
                    session.invoke("close", {})
                    self.assertEqual(session.invoke("audit", {})["final_count"], 1)


class WrapperValueTests(unittest.TestCase):
    """Codex: execute the real wrapper before any serializer sees unsupported objects."""

    compiler: Path

    # Locate an existing compiler for bounded synthetic wrapper evaluation.
    @classmethod
    def setUpClass(cls) -> None:
        cls.compiler = fixture_compiler()

    # Run a generated wrapper; raw is the exact synthetic method body under test.
    def wrapped(self, raw: str, limits: Limits | None = None, extra: str = "") -> JsonObject:
        body: str = wrap_script(raw.encode("utf-8"), "run-fixture", "R-1", "read-one", limits or Limits(), SecretGuard()).decode("utf-8")
        source: str = FIXTURE.split("public static class VisualFixture {")[0] + extra + r'''
public static class WrapperFixture {
    private static object Read() { /* WRAPPER */ }
    public static int Main() {
        Dictionary<string, object> result = Read() as Dictionary<string, object>;
        if (result == null || !result.ContainsKey("value_error")) {
            Console.Write("{\"legacy_unsafe\":true}"); return 0;
        }
        Console.Write(new JavaScriptSerializer().Serialize(result));
        return 0;
    }
}
'''
        return compile_fixture(self, self.compiler, source.replace("/* WRAPPER */", body), [])

    # Ordinary scalars, arrays and string-key dictionaries preserve their real values.
    def test_real_wrapper_projects_plain_json_without_default_values(self) -> None:
        result: JsonObject = self.wrapped('return new Dictionary<string, object> { {"zero", 0}, {"off", false}, {"missing", null}, {"counts", new List<int> { 2, 4 }} };')
        self.assertEqual(result.get("value"), {"zero": 0, "off": False, "missing": None, "counts": [2, 4]})
        self.assertIsNone(result["value_error"])
        self.assertEqual(result["frame"], 23)
        self.assertEqual(result["command_id"], "read-one")

    # A returned delegate must never be invoked or passed into a third-party serializer.
    def test_returned_delegate_is_a_reliable_contract_error(self) -> None:
        result: JsonObject = self.wrapped('return new Dictionary<string, object> { {"counts", (System.Func<List<int>>)delegate { throw new Exception("must not run"); }} };')
        self.assertEqual(result.get("value_error"), "unsupported_return_type")
        self.assertIsNone(result["value"])
        self.assertEqual(result["build_guid"], "fixture-build-v1")

    # Arbitrary getters and ToString must not run during return projection.
    def test_runtime_object_properties_and_strings_are_not_evaluated(self) -> None:
        result: JsonObject = self.wrapped("return new UntrustedReturn();", extra=r'''
public class UntrustedReturn {
    public int Count { get { throw new Exception("getter must not run"); } }
    public override string ToString() { throw new Exception("ToString must not run"); }
}
''')
        self.assertEqual(result["value_error"], "unsupported_return_type")
        self.assertIsNone(result["value"])

    # Cycles, depth, node count, output bytes and non-finite numbers remain bounded.
    def test_cycles_limits_and_nonfinite_numbers_produce_fixed_errors(self) -> None:
        variants: list[tuple[str, Limits, str]] = [
            ("List<object> items = new List<object>(); items.Add(items); return items;", Limits(), "return_value_budget"),
            ("return new int[20];", Limits(json_nodes=260), "return_value_budget"),
            ('return new string(\'x\', 2048);', Limits(value_bytes=1024), "return_value_budget"),
            ("return System.Double.NaN;", Limits(), "non_finite_return_number"),
            ("return new Dictionary<int, int> { { 1, 3 } };", Limits(), "unsupported_return_type"),
        ]
        for body, limits, expected in variants:
            with self.subTest(body=body):
                result: JsonObject = self.wrapped(body, limits)
                self.assertEqual(result["value_error"], expected)
                self.assertIsNone(result["value"])


class BuiltinButtonTests(unittest.TestCase):
    """Codex: compile and execute selection and clicks on isolated descendant controls."""

    compiler: Path

    # Use only the already installed framework compiler.
    @classmethod
    def setUpClass(cls) -> None:
        cls.compiler = fixture_compiler()

    # Build a synthetic container with a descendant button; body is production C#.
    def execute_button(self, body: bytes, mode: str = "custom") -> JsonObject:
        source: str = FIXTURE.split("public static class VisualFixture {")[0] + r'''
public static class ButtonFixture {
    private static object Run() { /* BUTTON_BODY */ }
    public static int Main(string[] args) {
        string mode = args[0];
        UnityEngine.GameObject root = new UnityEngine.GameObject("Root"); root.instanceID = -10;
        UnityEngine.GameObject container = new UnityEngine.GameObject("Container"); container.instanceID = -20;
        root.transform.children.Add(container.transform); container.transform.parent = root.transform;
        UnityEngine.GameObject actual = new UnityEngine.GameObject("Actual"); actual.instanceID = -30;
        container.transform.children.Add(actual.transform); actual.transform.parent = container.transform;
        UnityEngine.Resources.root = root.transform;
        GameButton custom = new GameButton { instanceID = mode == "replaced" ? -32 : -31, interactable = true };
        UnityEngine.UI.Button native = new UnityEngine.UI.Button { instanceID = -33 };
        if (mode != "native") { actual.Attach(custom); }
        if (mode == "native" || mode == "both") { actual.Attach(native); }
        if (mode == "inactive") { actual.activeInHierarchy = false; }
        if (mode == "blocked") { custom.groupAllowed = false; }
        if (mode == "disabled") { custom.enabled = false; }
        if (mode == "duplicate") {
            UnityEngine.GameObject other = new UnityEngine.GameObject("Actual"); other.instanceID = -40;
            container.transform.children.Add(other.transform); other.transform.parent = container.transform;
            other.Attach(new GameButton { instanceID = -41, interactable = true });
        }
        object result = null; string error = null;
        try { result = Run(); } catch (Exception exception) { error = exception.GetType().Name; }
        Console.Write(new JavaScriptSerializer().Serialize(new Dictionary<string, object> {
            {"result", result}, {"error", error}, {"custom_calls", custom.calls}, {"native_calls", native.onClick.calls} }));
        return 0;
    }
}
'''
        return compile_fixture(self, self.compiler, source.replace("/* BUTTON_BODY */", body.decode("utf-8")), [mode])

    # Obtain the actual generated observation; no prebuilt expected runtime rows are used.
    def before(self, mode: str = "custom") -> JsonObject:
        result: JsonObject = self.execute_button(builtin_observation("buttons", {"root": "Root/Container"}), mode)
        self.assertIsNone(result["error"])
        self.assertEqual(result["custom_calls"], 0)
        self.assertEqual(result["native_calls"], 0)
        return {"value": result["result"]}

    # The actual control may be below a container; prefer its GameButton when both exist.
    def test_button_observation_finds_descendant_and_actual_component(self) -> None:
        actual: JsonObject = cast(JsonObject, self.before("both")["value"])
        rows: list[JsonObject] = cast(list[JsonObject], actual["nodes"])
        self.assertEqual(actual["count"], 1)
        self.assertEqual(rows[0]["path"], "Root/Container/Actual")
        self.assertEqual(rows[0]["component_type"], "GameButton")
        self.assertEqual(rows[0]["instance_id"], -31)
        self.assertEqual(rows[0]["button_count"], 1)
        self.assertTrue(rows[0]["effective_interactable"])

    # One generated action must call exactly one public method, including native fallback.
    def test_builtin_click_invokes_one_actual_public_method(self) -> None:
        for mode in ("custom", "both", "native"):
            with self.subTest(mode=mode):
                body: bytes = builtin_button_click({"path": "Root/Container/Actual"}, self.before(mode))
                result: JsonObject = self.execute_button(body, mode)
                self.assertIsNone(result["error"])
                self.assertEqual(cast(JsonObject, result["result"])["method_called"], True)
                self.assertEqual(result["custom_calls"], 0 if mode == "native" else 1)
                self.assertEqual(result["native_calls"], 1 if mode == "native" else 0)

    # Changed instances, duplicate paths and disabled/group-blocked controls reject before call.
    def test_runtime_identity_and_interaction_changes_prevent_the_call(self) -> None:
        body: bytes = builtin_button_click({"path": "Root/Container/Actual"}, self.before())
        for mode in ("replaced", "duplicate", "inactive", "disabled", "blocked"):
            with self.subTest(mode=mode):
                result: JsonObject = self.execute_button(body, mode)
                self.assertIsNotNone(result["error"])
                self.assertEqual(result["custom_calls"], 0)
                self.assertEqual(result["native_calls"], 0)

    # A container, duplicate path or incomplete/disabled observed row is not a click target.
    def test_selector_errors_are_rejected_before_an_action_is_generated(self) -> None:
        before: JsonObject = self.before()
        with self.assertRaises(InputError):
            builtin_button_click({"path": "Root/Container"}, before)
        original: JsonObject = cast(JsonObject, before["value"])
        row: JsonObject = cast(list[JsonObject], original["nodes"])[0]
        variants: list[JsonObject] = [
            {**original, "truncated": True},
            {**original, "count": 2, "nodes": [row, row]},
            *[{**original, "nodes": [{**row, **change}]} for change in (
                {"active": False}, {"instance_id": 0}, {"instance_id": True}, {"button_count": 2}, {"click_method": None})],
        ]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(InputError):
                builtin_button_click({"path": "Root/Container/Actual"}, {"value": value})
