// ========================================================================
// Copyright (c) 2022 ChangYou, All rights reserved.
// http://www.changyou.com/
// 
// Filename:    PreloaderCoder.cs
// Time:        2025-05-27 20:35:55
// Author:      xiangjinbao
// Email:       xiangjinbao@cyou-inc.com
// Version:     v1.0.0
// Description: PreloaderCoder  简单预加载控制器，todo 待优化
// ========================================================================

using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using GameFramework.Core;
using HybridCLR;
using UnityEngine;

namespace GameFramework.Logic
{
	public class PreloaderCoder : IPreloader
	{
		private static Assembly s_LogicAssembly;
		
		private static readonly List<string> m_AotDllList = new();
		private static readonly string m_LogicDllPath = "Code/CyStarRoad.bytes";
		
		public static Assembly LogicAssembly => s_LogicAssembly;
		public static List<string> AotDllList => m_AotDllList;
		
		public static object Invoke(string className, string funcName, object obj = null, object[] param = null)
		{
			if (s_LogicAssembly == null) return null;
			Type classType = s_LogicAssembly.GetType(className);
			MethodInfo methodInfo = classType.GetMethod(funcName);
			return methodInfo.Invoke(obj, param);
		}

		public static Type LoadedTypes(string className)
		{
			return s_LogicAssembly.GetType(className);
		}

		/// <summary>
		/// 添加1热更新包。
		/// </summary>
		public int Count => m_AotDllList.Count + 1;

		private Action<PreloadAssetInfo> m_OnFinishCallback;

		static PreloaderCoder()
		{
			InitDllList();
		}

		private static void InitDllList()
		{
			// 只统计真正会被加载的条目：Count 与 LoadAllDll 中的回调次数必须严格一致。
			// AOT 补充元数据仅 IL2CPP 后端需要，LoadAllDll 用 ENABLE_IL2CPP 守卫整段跳过，
			// 因此这里必须用同一个宏守卫。若在 Mono 下仍填充 m_AotDllList，
			// Count 会比实际回调多 5，PreloadController 的总数被抬高，
			// PreloadAssetInfo.GetProgress() 恒小于 1，ProcedurePreload 将永久卡住无法切换流程。
#if ENABLE_IL2CPP
			if (!Context.IsEditorCode)
			{
				m_AotDllList.AddRange(new string[]
				{
						"mscorlib",
						"System",
						"System.Core",
						"GameFramework.Base",
						"GameFramework.Core",
				});
			}
#endif
		}

		public void Start(Action<PreloadAssetInfo> callback)
		{
			m_OnFinishCallback = callback;
			CoroutineComponent.Inst.StartCoroutine(LoadAllDll());
		}

		private IEnumerator LoadAllDll()
		{
			if (Context.IsEditorCode)
			{
				yield return DownLoadUtils.InitPackageVersionAndResMd5();
				s_LogicAssembly = AppDomain.CurrentDomain.GetAssemblies().First(a => a.GetName().Name == "CyStarRoad");
				yield return null;
				m_OnFinishCallback?.Invoke(new PreloadAssetInfo(m_LogicDllPath, s_LogicAssembly, true));
			}
			else
			{
				// AOT 补充元数据仅 IL2CPP 后端需要：HybridCLR 的 LoadMetadataForAOTAssembly 是
				// [MethodImpl(MethodImplOptions.InternalCall)] 原生实现，Mono 后端没有该实现，调用会失败。
				// ENABLE_IL2CPP 只在 IL2CPP 后端定义，用它做守卫可精确区分，Mono 包整体跳过该段。
				// Mono 下热更程序集走原生 Assembly.Load，逻辑 Dll 的加载代码在守卫之外，不受影响。
#if ENABLE_IL2CPP
				HomologousImageMode mode = HomologousImageMode.SuperSet;
				foreach (var aotDllName in m_AotDllList)
				{
					string aotDllPath = $"Code/{aotDllName}.bytes";
					yield return LoadAsset(aotDllPath, (result) =>
					{
						TextAsset textAsset = result.textAsset;
						LoadImageErrorCode err = RuntimeApi.LoadMetadataForAOTAssembly(textAsset.bytes, mode);
						if (err != LoadImageErrorCode.OK)
						{
							GameLog.LogError($"LoadMetadataForAOTAssembly error {err}");
						}
						m_OnFinishCallback?.Invoke(new PreloadAssetInfo(aotDllPath, textAsset, false));
					});
				}
#endif
				yield return LoadAsset(m_LogicDllPath, (result) =>
				{
					TextAsset textAsset = result.textAsset;
					s_LogicAssembly = Assembly.Load(textAsset.bytes);
					m_OnFinishCallback?.Invoke(new PreloadAssetInfo(m_LogicDllPath, textAsset, false));
				});
				yield return null;
			}
		}

		/// <summary>
		/// 加载资源Asset
		/// </summary>
		/// <param name="assetPath"></param>
		/// <param name="callback"></param>
		/// <returns></returns>
		private IEnumerator LoadAsset(string assetPath, Action<ResAssetResult> callback)
		{
			bool isDone = false;
			GameRes.LoadAssetAsync(assetPath, (result) =>
			{
				callback?.Invoke(result);
				isDone = true;
			});
			while (!isDone)
			{
				yield return null;
			}
		}
	}
}