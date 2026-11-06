// 创建日期：2026-10-26；作者：Cyou。
// 功能：真实场景节点、严格反射观察/单次调用和标准 UI 控件；基础参数：选择器、当前实例、已加载程序集/MVID、精确成员/签名与预算。
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD && MONO_PIPELINE_FUNCTIONTEST && !UNITY_EDITOR && !ENABLE_IL2CPP
using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

internal static class MonoPipelineReflection
{
    internal const int MaximumNodes = 32768;
    private const int MaximumScenes = 64;
    private const int MaximumDepth = 128;
    private const int MaximumResults = 512;
    private const int MaximumAssemblies = 256;
    private const int MaximumTypesInspected = 65536;
    private const int MaximumMembers = 64;
    private const int MaximumMemberDepth = 8;
    private const int MaximumArguments = 16;
    private const int MaximumJsonNodes = 4096;
    private const int MaximumJsonDepth = 8;
    private const int MaximumStringCharacters = 65536;

    // 功能：校验可配置整数预算；参数 maximum 是硬上限，不把越界请求裁成默认值。
    private static void Budget(int value, int maximum)
    {
        if (value < 1 || value > maximum) throw new ArgumentOutOfRangeException("budget");
    }

    // 功能：取得真实已加载场景和授权取证驱动所在持久场景；参数无，不枚举项目 Prefab 资源。
    private static List<Scene> LoadedScenes()
    {
        int count = SceneManager.sceneCount;
        if (count < 0 || count > MaximumScenes) throw new InvalidOperationException("loaded_scene_budget_exceeded");
        List<Scene> scenes = new List<Scene>();
        for (int index = 0; index < count; index++)
        {
            Scene scene = SceneManager.GetSceneAt(index);
            if (scene.IsValid() && scene.isLoaded) scenes.Add(scene);
        }
        Scene persistent = MonoPipelineEvidence.PersistentScene;
        if (persistent.IsValid() && persistent.isLoaded && !scenes.Contains(persistent)) scenes.Add(persistent);
        return scenes;
    }

    // 功能：在总节点预算内逐节点遍历；参数 includeInactive 明确控制候选，超预算报错不伪装全集。
    private static List<GameObject> Nodes(bool includeInactive, int maximum)
    {
        Budget(maximum, MaximumNodes);
        List<GameObject> result = new List<GameObject>();
        Stack<Transform> pending = new Stack<Transform>();
        foreach (Scene scene in LoadedScenes())
        {
            GameObject[] roots = scene.GetRootGameObjects();
            if (roots == null || roots.Length + pending.Count > maximum) throw new InvalidOperationException("scene_roots_budget_exceeded");
            foreach (GameObject root in roots)
            {
                if (root != null && root.transform != null) pending.Push(root.transform);
            }
        }
        int visited = 0;
        while (pending.Count > 0)
        {
            if (++visited > maximum) throw new InvalidOperationException("node_discovery_budget_exceeded");
            Transform transform = pending.Pop();
            if (transform == null || transform.gameObject == null) continue;
            GameObject node = transform.gameObject;
            if (!node.scene.IsValid() || !node.scene.isLoaded || MonoPipelineEvidence.IsOwnNode(node)) continue;
            if (!includeInactive && !node.activeInHierarchy) continue;
            result.Add(node);
            if (transform.childCount + pending.Count + visited > maximum) throw new InvalidOperationException("node_discovery_budget_exceeded");
            for (int child = 0; child < transform.childCount; child++)
            {
                Transform item = transform.GetChild(child);
                if (item != null) pending.Push(item);
            }
        }
        return result;
    }

    // 功能：生成场景身份+名称/同级序号的可重定位候选；参数 node 必须是当前加载对象，实例身份另行核验。
    private static string Selector(GameObject node)
    {
        if (node == null || !node.scene.IsValid() || !node.scene.isLoaded) throw new InvalidOperationException("node_not_loaded");
        List<string> parts = new List<string>();
        Transform current = node.transform;
        while (current != null)
        {
            if (parts.Count >= MaximumDepth) throw new InvalidOperationException("hierarchy_depth_exceeded");
            parts.Add(Uri.EscapeDataString(current.name) + "[" + current.GetSiblingIndex().ToString(System.Globalization.CultureInfo.InvariantCulture) + "]");
            current = current.parent;
        }
        parts.Reverse();
        string sceneIdentity = string.IsNullOrEmpty(node.scene.path) ? node.scene.name : node.scene.path;
        return "scene=" + Uri.EscapeDataString(sceneIdentity) + "|node=/" + string.Join("/", parts.ToArray());
    }

    // 功能：输出当前真实节点和组件身份；参数 node 不缓存到后续动作。
    private static Dictionary<string, object> DescribeNode(GameObject node)
    {
        if (node == null) throw new InvalidOperationException("node_destroyed");
        Component[] components = node.GetComponents<Component>();
        if (components == null || components.Length > MaximumResults) throw new InvalidOperationException("component_budget_exceeded");
        List<object> items = new List<object>();
        foreach (Component component in components)
        {
            if (component == null)
            {
                items.Add(new Dictionary<string, object> { { "missing_script", true } });
                continue;
            }
            Type type = component.GetType();
            Dictionary<string, object> identity = TypeIdentity(type);
            identity.Add("instance_id", component.GetInstanceID());
            items.Add(identity);
        }
        return new Dictionary<string, object> {
            { "selector", Selector(node) }, { "instance_id", node.GetInstanceID() }, { "name", node.name },
            { "scene", node.scene.name }, { "scene_path", node.scene.path }, { "scene_handle", node.scene.handle },
            { "active_self", node.activeSelf }, { "active_in_hierarchy", node.activeInHierarchy },
            { "components", items }, { "frame", Time.frameCount }
        };
    }

    // 功能：有界候选发现；参数过滤只改变候选列表，截断有显式标记，不能直接证明唯一目标。
    internal static object Discover(string scene, string nameContains, bool includeInactive, int maxNodes, int maxResults)
    {
        Budget(maxResults, MaximumResults);
        List<GameObject> nodes = Nodes(includeInactive, maxNodes);
        List<object> matches = new List<object>();
        int total = 0;
        foreach (GameObject node in nodes)
        {
            if (node == null) continue;
            if (!string.IsNullOrEmpty(scene) && node.scene.name != scene && node.scene.path != scene) continue;
            if (!string.IsNullOrEmpty(nameContains) && node.name.IndexOf(nameContains, StringComparison.Ordinal) < 0) continue;
            total++;
            if (matches.Count < maxResults) matches.Add(DescribeNode(node));
        }
        return new Dictionary<string, object> { { "nodes", matches }, { "matched_count", total },
            { "inspected_nodes", nodes.Count }, { "truncated", total > maxResults }, { "loaded_nodes_only", true } };
    }

    // 功能：重新遍历并解析精确唯一目标；参数 instanceId 必须来自当前 before，不复用旧句柄。
    internal static GameObject Resolve(string selector, int instanceId)
    {
        if (instanceId == 0) throw new ArgumentException("current_instance_id_required");
        GameObject found = null;
        foreach (GameObject node in Nodes(true, MaximumNodes))
        {
            if (node == null || !string.Equals(Selector(node), selector, StringComparison.Ordinal)) continue;
            if (found != null) throw new InvalidOperationException("selector_ambiguous");
            found = node;
        }
        if (found == null) throw new InvalidOperationException("target_missing");
        if (found.GetInstanceID() != instanceId) throw new InvalidOperationException("target_rebuilt_relocate_required");
        return found;
    }

    // 功能：输出真实类型、来源和 MVID；参数 type 仅来自当前已加载集合，动态来源不伪造文件路径。
    private static Dictionary<string, object> TypeIdentity(Type type)
    {
        if (type == null || type.Assembly == null || type.Module == null) throw new InvalidOperationException("type_metadata_absent");
        string location = null;
        if (!type.Assembly.IsDynamic)
        {
            try { location = type.Assembly.Location; }
            catch (NotSupportedException) { location = null; }
        }
        return new Dictionary<string, object> { { "type", type.FullName }, { "assembly", type.Assembly.FullName },
            { "mvid", type.Module.ModuleVersionId.ToString("D") }, { "location", location }, { "dynamic", type.Assembly.IsDynamic } };
    }

    // 功能：有界读取已加载类型及加载诊断；参数 prefix 为限定前缀，截断/加载错误明确返回而非默认计数。
    internal static object LoadedTypes(string prefix, int maxTypes)
    {
        Budget(maxTypes, MaximumResults);
        Assembly[] assemblies = AppDomain.CurrentDomain.GetAssemblies();
        if (assemblies == null || assemblies.Length > MaximumAssemblies) throw new InvalidOperationException("assembly_budget_exceeded");
        List<object> result = new List<object>();
        List<object> diagnostics = new List<object>();
        int inspected = 0;
        bool truncated = false;
        foreach (Assembly assembly in assemblies)
        {
            if (assembly == null) continue;
            Type[] types;
            try { types = assembly.GetTypes(); }
            catch (ReflectionTypeLoadException exception)
            {
                types = exception.Types;
                diagnostics.Add(new Dictionary<string, object> { { "assembly", assembly.FullName }, { "error", exception.Message } });
            }
            if (types == null) throw new InvalidOperationException("loaded_type_collection_absent");
            foreach (Type type in types)
            {
                if (++inspected > MaximumTypesInspected) { truncated = true; break; }
                if (type == null || (!string.IsNullOrEmpty(prefix) && (type.FullName == null || !type.FullName.StartsWith(prefix, StringComparison.Ordinal)))) continue;
                if (result.Count == maxTypes) { truncated = true; continue; }
                result.Add(TypeIdentity(type));
            }
            if (inspected > MaximumTypesInspected) break;
        }
        return new Dictionary<string, object> { { "types", result }, { "diagnostics", diagnostics }, { "truncated", truncated },
            { "complete", !truncated && diagnostics.Count == 0 }, { "inspected_types", inspected }, { "assemblies", assemblies.Length },
            { "roslyn_metadata_registration_performed", false } };
    }

    // 功能：唯一完整类型解析并核对来源/MVID；参数不接受程序集加载或同名 DLL 的重复注册。
    private static Type ResolveType(string typeName, string assemblyFullName, string moduleMvid)
    {
        if (string.IsNullOrEmpty(typeName) || string.IsNullOrEmpty(assemblyFullName) || string.IsNullOrEmpty(moduleMvid))
            throw new ArgumentException("type_assembly_mvid_required");
        Assembly[] assemblies = AppDomain.CurrentDomain.GetAssemblies();
        if (assemblies == null || assemblies.Length > MaximumAssemblies) throw new InvalidOperationException("assembly_budget_exceeded");
        Type found = null;
        foreach (Assembly assembly in assemblies)
        {
            if (assembly == null) continue;
            Type candidate = assembly.GetType(typeName, false, false);
            if (candidate == null) continue;
            if (found != null) throw new InvalidOperationException("loaded_type_ambiguous");
            found = candidate;
        }
        if (found == null) throw new InvalidOperationException("loaded_type_missing:" + typeName);
        if (found.Assembly.FullName != assemblyFullName || !string.Equals(found.Module.ModuleVersionId.ToString("D"), moduleMvid, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("loaded_type_source_or_mvid_changed");
        return found;
    }

    // 功能：解析精确唯一存活组件；参数 type 必须是已验证真实组件类型，不接受派生类型替代。
    private static Component ResolveComponent(GameObject node, Type type)
    {
        if (node == null || type == null || !typeof(Component).IsAssignableFrom(type)) throw new ArgumentException("component_target_invalid");
        Component[] components = node.GetComponents(type);
        if (components == null) throw new InvalidOperationException("component_collection_absent");
        Component found = null;
        foreach (Component component in components)
        {
            if (component == null || component.GetType() != type) continue;
            if (found != null) throw new InvalidOperationException("component_ambiguous");
            found = component;
        }
        if (found == null) throw new InvalidOperationException("component_missing");
        return found;
    }

    // 功能：读取明确字段或非索引属性；参数隐藏同名成员/反射 getter 异常都必须拒绝而非填默认值。
    private static object ReadMember(object source, string name)
    {
        if (source == null || (source is UnityEngine.Object && (UnityEngine.Object)source == null)) throw new InvalidOperationException("member_owner_missing");
        MemberInfo selected = null;
        Type current = source.GetType();
        int depth = 0;
        while (current != null)
        {
            if (++depth > MaximumDepth) throw new InvalidOperationException("member_inheritance_budget_exceeded");
            MemberInfo[] members = current.GetMember(name, MemberTypes.Field | MemberTypes.Property,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
            if (members == null) throw new InvalidOperationException("member_metadata_absent");
            foreach (MemberInfo member in members)
            {
                if (selected != null) throw new InvalidOperationException("member_ambiguous:" + name);
                selected = member;
            }
            current = current.BaseType;
        }
        FieldInfo field = selected as FieldInfo;
        if (field != null) return field.GetValue(source);
        PropertyInfo property = selected as PropertyInfo;
        if (property == null || property.GetIndexParameters().Length != 0 || property.GetGetMethod(true) == null)
            throw new InvalidOperationException("member_missing_or_not_readable:" + name);
        return property.GetValue(source, null);
    }

    // 功能：只转换有界实际 JSON 值，不自动遍历任意对象 getter；参数预算在整次观察共用。
    private static object JsonValue(object value, int depth, ref int count)
    {
        if (++count > MaximumJsonNodes || depth > MaximumJsonDepth) throw new InvalidOperationException("json_value_budget_exceeded");
        if (value == null) return null;
        Type type = value.GetType();
        if (type == typeof(string))
        {
            if (((string)value).Length > MaximumStringCharacters) throw new InvalidOperationException("json_text_budget_exceeded");
            return value;
        }
        if (type == typeof(bool) || type == typeof(byte) || type == typeof(sbyte) || type == typeof(short)
            || type == typeof(ushort) || type == typeof(int) || type == typeof(uint) || type == typeof(long) || type == typeof(ulong)) return value;
        if (type == typeof(float))
        {
            float number = (float)value;
            if (float.IsNaN(number) || float.IsInfinity(number)) throw new InvalidOperationException("non_finite_actual_value");
            return value;
        }
        if (type == typeof(double))
        {
            double number = (double)value;
            if (double.IsNaN(number) || double.IsInfinity(number)) throw new InvalidOperationException("non_finite_actual_value");
            return value;
        }
        IDictionary dictionary = value as IDictionary;
        if (dictionary != null)
        {
            Dictionary<string, object> result = new Dictionary<string, object>();
            foreach (DictionaryEntry entry in dictionary)
            {
                string key = entry.Key as string;
                if (key == null || result.ContainsKey(key)) throw new InvalidOperationException("json_dictionary_key_invalid");
                result.Add(key, JsonValue(entry.Value, depth + 1, ref count));
            }
            return result;
        }
        IList list = value as IList;
        if (list != null)
        {
            if (list.Count > MaximumJsonNodes) throw new InvalidOperationException("json_array_budget_exceeded");
            List<object> result = new List<object>();
            foreach (object item in list) result.Add(JsonValue(item, depth + 1, ref count));
            return result;
        }
        throw new InvalidOperationException("actual_value_type_requires_explicit_member_projection:" + type.FullName);
    }

    // 功能：读取明确成员链和当前节点身份；参数路径深度/成员数有界，不构造业务默认值。
    internal static object Observe(string target, int instanceId, string typeName, string assembly, string mvid, string[] members)
    {
        if (members == null) throw new ArgumentNullException("members");
        Budget(members.Length, MaximumMembers);
        GameObject node = Resolve(target, instanceId);
        object owner = node;
        if (!string.IsNullOrEmpty(typeName)) owner = ResolveComponent(node, ResolveType(typeName, assembly, mvid));
        Dictionary<string, object> values = new Dictionary<string, object>();
        int count = 0;
        foreach (string member in members)
        {
            if (string.IsNullOrEmpty(member) || values.ContainsKey(member)) throw new ArgumentException("member_path_invalid_or_duplicate");
            string[] parts = member.Split('.');
            Budget(parts.Length, MaximumMemberDepth);
            object actual = owner;
            foreach (string part in parts) actual = ReadMember(actual, part);
            values.Add(member, JsonValue(actual, 0, ref count));
        }
        return new Dictionary<string, object> { { "node", DescribeNode(node) }, { "owner_type", owner.GetType().FullName }, { "members", values }, { "unique_count", 1 } };
    }

    // 功能：核对唯一声明方法及精确参数类型，再只 Invoke 一次；参数 node=null 仅表示明确静态调用。
    internal static object Invoke(GameObject node, string typeName, string assembly, string mvid, string methodName,
        string[] parameterTypes, object[] arguments)
    {
        Type type = ResolveType(typeName, assembly, mvid);
        if (string.IsNullOrEmpty(methodName) || parameterTypes == null || arguments == null
            || parameterTypes.Length != arguments.Length || arguments.Length > MaximumArguments) throw new ArgumentException("method_signature_invalid");
        bool isStatic = node == null;
        object owner = isStatic ? null : ResolveComponent(node, type);
        if (!isStatic)
        {
            Behaviour behaviour = owner as Behaviour;
            Selectable selectable = owner as Selectable;
            if (node == null || !node.activeInHierarchy || (behaviour != null && !behaviour.isActiveAndEnabled)
                || (selectable != null && !selectable.IsInteractable()))
                throw new InvalidOperationException("component_not_currently_operable");
        }
        MethodInfo selected = null;
        MethodInfo[] methods = type.GetMethods(BindingFlags.DeclaredOnly | BindingFlags.Public | BindingFlags.NonPublic
            | (isStatic ? BindingFlags.Static : BindingFlags.Instance));
        if (methods == null) throw new InvalidOperationException("method_metadata_absent");
        foreach (MethodInfo method in methods)
        {
            if (method == null || method.Name != methodName || method.ContainsGenericParameters) continue;
            ParameterInfo[] parameters = method.GetParameters();
            if (parameters == null || parameters.Length != parameterTypes.Length) continue;
            bool exact = true;
            for (int index = 0; index < parameters.Length; index++)
            {
                if (parameters[index] == null || parameters[index].ParameterType.FullName != parameterTypes[index]) exact = false;
            }
            if (!exact) continue;
            if (selected != null) throw new InvalidOperationException("method_signature_ambiguous");
            selected = method;
        }
        if (selected == null) throw new InvalidOperationException("exact_method_missing");
        ParameterInfo[] signature = selected.GetParameters();
        for (int index = 0; index < signature.Length; index++)
        {
            Type parameter = signature[index].ParameterType;
            if (parameter.IsByRef || parameter.IsPointer || (arguments[index] == null && parameter.IsValueType
                && Nullable.GetUnderlyingType(parameter) == null) || (arguments[index] != null && !parameter.IsInstanceOfType(arguments[index])))
                throw new ArgumentException("argument_type_mismatch_no_implicit_conversion");
        }
        selected.Invoke(owner, arguments);
        return new Dictionary<string, object> { { "invocation_count", 1 }, { "type_identity", TypeIdentity(type) },
            { "method", selected.Name }, { "parameter_types", parameterTypes }, { "independent_after_required", true } };
    }

    // 功能：操作精确标准 Button；参数当前实例必须可交互，定制组件改用已验证的明确反射接口。
    internal static object ClickButton(string target, int instanceId)
    {
        GameObject node = Resolve(target, instanceId);
        Button button = ResolveComponent(node, typeof(Button)) as Button;
        if (button == null || !button.enabled || !node.activeInHierarchy || !button.IsActive() || !button.IsInteractable() || button.onClick == null)
            throw new InvalidOperationException("button_not_operable");
        button.onClick.Invoke();
        return new Dictionary<string, object> { { "invocation_count", 1 }, { "independent_after_required", true }, { "input_kind", "onClick_programmatic_not_pointer_input" } };
    }

    // 功能：操作精确标准 Toggle；参数同值时不重复事件，不把 setter 回执当业务预期。
    internal static object SetToggle(string target, int instanceId, bool value)
    {
        GameObject node = Resolve(target, instanceId);
        Toggle toggle = ResolveComponent(node, typeof(Toggle)) as Toggle;
        if (toggle == null || !toggle.enabled || !node.activeInHierarchy || !toggle.IsActive() || !toggle.IsInteractable())
            throw new InvalidOperationException("toggle_not_operable");
        int invoked = toggle.isOn == value ? 0 : 1;
        if (invoked == 1) toggle.isOn = value;
        return new Dictionary<string, object> { { "invocation_count", invoked }, { "requested_value", value }, { "independent_after_required", true } };
    }
}
#endif
