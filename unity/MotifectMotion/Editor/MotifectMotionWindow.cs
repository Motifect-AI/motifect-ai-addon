using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace Motifect.Motion
{
    public sealed class MotifectMotionWindow : EditorWindow
    {
        private const string PrefApiKey = "MotifectMotion.ApiKey";
        private const string PrefBaseUrl = "MotifectMotion.BaseUrl";
        private const string ImportFolder = "Assets/Motifect/Generated";

        private string _apiKey = "";
        private string _baseUrl = MotifectClient.DefaultBaseUrl;
        private string _prompt = "A person turns sharply, regains balance, and continues walking.";
        private int _durationSeconds = 8;
        private int _modelIndex = 1;
        private int _creditBalance = -1;
        private string _status = "Ready.";
        private bool _isBusy;
        private CancellationTokenSource _cts;

        [MenuItem("Window/Motifect/Motion Generator")]
        public static void Open()
        {
            var window = GetWindow<MotifectMotionWindow>("Motifect Motion");
            window.minSize = new Vector2(420, 360);
            window.Show();
        }

        private void OnEnable()
        {
            _apiKey = EditorPrefs.GetString(PrefApiKey, "");
            _baseUrl = EditorPrefs.GetString(PrefBaseUrl, MotifectClient.DefaultBaseUrl);
        }

        private void OnDisable()
        {
            CancelGeneration();
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Motifect Motion", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Requires a motifect.io account, API key (mk_live_...), and credits.",
                MessageType.Info);

            EditorGUI.BeginDisabledGroup(_isBusy);

            _apiKey = EditorGUILayout.PasswordField("API Key", _apiKey);
            _baseUrl = EditorGUILayout.TextField("API Base URL", _baseUrl);

            EditorGUILayout.Space(6);
            EditorGUILayout.LabelField("Prompt (English, 10–180 chars)", EditorStyles.miniBoldLabel);
            _prompt = EditorGUILayout.TextArea(_prompt, GUILayout.MinHeight(72));

            _durationSeconds = EditorGUILayout.IntSlider("Duration (seconds)", _durationSeconds, 2, 10);
            _modelIndex = EditorGUILayout.Popup(
                "Model",
                _modelIndex,
                new[]
                {
                    "Motifect v3 Fast (8 credits)",
                    "Motifect v3 (16 credits)",
                    "Kimodo Human (20 credits)",
                });

            EditorGUILayout.Space(8);
            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("Refresh Credits", GUILayout.Height(28)))
                {
                    _ = RefreshCreditsAsync();
                }

                if (GUILayout.Button("Generate Motion", GUILayout.Height(28)))
                {
                    _ = GenerateMotionAsync();
                }
            }

            EditorGUI.EndDisabledGroup();

            if (_isBusy && GUILayout.Button("Cancel"))
            {
                CancelGeneration();
                _status = "Cancelled.";
                Repaint();
            }

            EditorGUILayout.Space(8);
            var creditsText = _creditBalance >= 0 ? _creditBalance.ToString() : "—";
            EditorGUILayout.LabelField("Credits", creditsText);
            EditorGUILayout.LabelField("Status", _status, EditorStyles.wordWrappedLabel);
        }

        private void SavePrefs()
        {
            EditorPrefs.SetString(PrefApiKey, _apiKey ?? "");
            EditorPrefs.SetString(PrefBaseUrl, string.IsNullOrWhiteSpace(_baseUrl) ? MotifectClient.DefaultBaseUrl : _baseUrl);
        }

        private string SelectedModelKey() => MotifectModels.Choices[Mathf.Clamp(_modelIndex, 0, MotifectModels.Choices.Length - 1)].Key;

        private async Task RefreshCreditsAsync()
        {
            if (string.IsNullOrWhiteSpace(_apiKey))
            {
                _status = "Set your API key first.";
                Repaint();
                return;
            }

            SavePrefs();
            try
            {
                using var client = new MotifectClient(_apiKey, _baseUrl);
                _creditBalance = await client.GetBalanceAsync();
                _status = "Credits refreshed.";
            }
            catch (Exception exc)
            {
                _status = exc.Message;
                Debug.LogError($"[Motifect] {exc}");
            }

            Repaint();
        }

        private async Task GenerateMotionAsync()
        {
            if (_isBusy)
            {
                return;
            }

            var prompt = (_prompt ?? "").Trim();
            if (prompt.Length < 10)
            {
                _status = "Prompt must be at least 10 characters.";
                Repaint();
                return;
            }

            if (string.IsNullOrWhiteSpace(_apiKey))
            {
                _status = "Set your API key first.";
                Repaint();
                return;
            }

            SavePrefs();
            _isBusy = true;
            _cts = new CancellationTokenSource();
            _status = "Submitting request…";
            Repaint();

            var tempPath = Path.Combine(Path.GetTempPath(), $"motifect_{Guid.NewGuid():N}.fbx");
            try
            {
                using var client = new MotifectClient(_apiKey, _baseUrl);
                var modelKey = SelectedModelKey();
                var work = await client.GenerateAndExportAsync(
                    prompt,
                    tempPath,
                    "fbx",
                    _durationSeconds,
                    modelKey,
                    onProgress: w =>
                    {
                        _status = MotifectClient.FormatWorkStatus(w);
                        EditorApplication.delayCall += Repaint;
                    },
                    cancellationToken: _cts.Token);

                var workId = work.Value<string>("id") ?? "motion";
                var assetPath = ImportMotion(tempPath, workId, prompt);
                _status = string.IsNullOrEmpty(assetPath)
                    ? $"Motion generated ({workId}) but import failed."
                    : $"Imported {assetPath}";
                await RefreshCreditsAsync();
            }
            catch (OperationCanceledException)
            {
                _status = "Cancelled.";
            }
            catch (Exception exc)
            {
                _status = exc.Message;
                Debug.LogError($"[Motifect] {exc}");
            }
            finally
            {
                if (File.Exists(tempPath))
                {
                    File.Delete(tempPath);
                }

                _isBusy = false;
                _cts?.Dispose();
                _cts = null;
                Repaint();
            }
        }

        private static string ImportMotion(string sourcePath, string workId, string prompt)
        {
            if (!File.Exists(sourcePath))
            {
                return null;
            }

            Directory.CreateDirectory(Path.Combine(Application.dataPath, "Motifect", "Generated"));
            var slug = Slugify(prompt);
            var fileName = $"Motifect_{slug}_{workId[..Math.Min(8, workId.Length)]}.fbx";
            var assetPath = $"{ImportFolder}/{fileName}";
            var projectRoot = Directory.GetParent(Application.dataPath)?.FullName;
            if (string.IsNullOrEmpty(projectRoot))
            {
                return null;
            }

            var destPath = Path.Combine(projectRoot, assetPath.Replace('/', Path.DirectorySeparatorChar));
            File.Copy(sourcePath, destPath, true);
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
            Debug.Log($"[Motifect] Imported {assetPath}");
            return assetPath;
        }

        private static string Slugify(string value)
        {
            var chars = value.ToLowerInvariant().ToCharArray();
            for (var i = 0; i < chars.Length; i++)
            {
                var c = chars[i];
                chars[i] = char.IsLetterOrDigit(c) ? c : '_';
            }

            var slug = new string(chars).Trim('_');
            if (slug.Length > 32)
            {
                slug = slug[..32];
            }

            return string.IsNullOrEmpty(slug) ? "motion" : slug;
        }

        private void CancelGeneration()
        {
            _cts?.Cancel();
        }
    }
}
