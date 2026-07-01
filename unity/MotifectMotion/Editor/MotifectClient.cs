using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace Motifect.Motion
{
    public sealed class MotifectApiException : Exception
    {
        public int? StatusCode { get; }

        public MotifectApiException(string message, int? statusCode = null, Exception inner = null)
            : base(message, inner)
        {
            StatusCode = statusCode;
        }
    }

    public static class MotifectModels
    {
        public static readonly (string Key, string Label)[] Choices =
        {
            ("motifect-v3-fast", "Motifect v3 Fast (8 credits)"),
            ("motifect-v3", "Motifect v3 (16 credits)"),
            ("kimodo-human", "Kimodo Human (20 credits)"),
        };
    }

    public sealed class MotifectClient : IDisposable
    {
        public const string DefaultBaseUrl = "https://api.motifect.io/api/v1";
        public const string DefaultUserAgent = "MotifectMotion/1.0 (Motifect Unity Client)";

        private readonly HttpClient _http;
        private readonly string _baseUrl;

        public MotifectClient(string apiKey, string baseUrl = DefaultBaseUrl, string userAgent = DefaultUserAgent)
        {
            if (string.IsNullOrWhiteSpace(apiKey))
            {
                throw new ArgumentException("API key is required.", nameof(apiKey));
            }

            _baseUrl = (baseUrl ?? DefaultBaseUrl).TrimEnd('/');
            _http = new HttpClient { Timeout = TimeSpan.FromSeconds(120) };
            _http.DefaultRequestHeaders.UserAgent.ParseAdd(userAgent);
            _http.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
            _http.DefaultRequestHeaders.Add("X-API-Key", apiKey.Trim());
        }

        public void Dispose() => _http.Dispose();

        public async Task<int> GetBalanceAsync(CancellationToken cancellationToken = default)
        {
            var payload = await RequestAsync("GET", "/credits/balance", null, cancellationToken);
            return payload.Value<int>("balance");
        }

        public async Task<string> GenerateAsync(
            string prompt,
            int durationSeconds,
            string modelKey,
            CancellationToken cancellationToken = default)
        {
            var body = new JObject
            {
                ["prompt"] = prompt,
                ["duration_seconds"] = durationSeconds,
                ["model_key"] = modelKey,
            };
            var payload = await RequestAsync("POST", "/motions/generate", body, cancellationToken);
            return payload["data"]?["work"]?["id"]?.Value<string>()
                ?? throw new MotifectApiException("Missing work id in generate response.");
        }

        public async Task<JObject> GetMotionAsync(string workId, CancellationToken cancellationToken = default)
        {
            var payload = await RequestAsync("GET", $"/motions/{workId}", null, cancellationToken);
            return payload["item"] as JObject ?? throw new MotifectApiException("Missing motion item.");
        }

        public async Task<JObject> ConvertAsync(string workId, string exportFormat, CancellationToken cancellationToken = default)
        {
            var body = new JObject { ["format"] = exportFormat };
            var payload = await RequestAsync("POST", $"/motions/{workId}/convert", body, cancellationToken);
            return payload["item"] as JObject ?? throw new MotifectApiException("Missing convert item.");
        }

        public static string FormatWorkStatus(JObject work)
        {
            var status = work.Value<string>("status") ?? "unknown";
            var progress = work["progress"];
            if (progress is JObject progressObj)
            {
                var message = progressObj.Value<string>("message") ?? progressObj.Value<string>("stage");
                if (!string.IsNullOrEmpty(message))
                {
                    return $"{status}: {message}";
                }
            }
            else if (progress != null && (progress.Type == JTokenType.Float || progress.Type == JTokenType.Integer))
            {
                var value = progress.Value<double>();
                var pct = value <= 1 ? (int)(value * 100) : (int)value;
                return $"{status} ({pct}%)";
            }

            return status;
        }

        public static string FindAssetUrl(JObject work, string exportFormat, string assetRole = "export_file")
        {
            if (work["assets"] is not JArray assets)
            {
                return null;
            }

            foreach (var asset in assets)
            {
                if (asset.Value<string>("format") != exportFormat)
                {
                    continue;
                }

                if (!string.IsNullOrEmpty(assetRole) && asset.Value<string>("asset_role") != assetRole)
                {
                    continue;
                }

                var url = asset.Value<string>("url");
                if (!string.IsNullOrEmpty(url))
                {
                    return url;
                }
            }

            return null;
        }

        public async Task<JObject> PollUntilCompleteAsync(
            string workId,
            Action<JObject> onProgress,
            float intervalSeconds = 3f,
            float timeoutSeconds = 600f,
            CancellationToken cancellationToken = default)
        {
            var deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
            while (DateTime.UtcNow < deadline)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var work = await GetMotionAsync(workId, cancellationToken);
                onProgress?.Invoke(work);

                var status = work.Value<string>("status");
                if (status == "completed")
                {
                    return work;
                }

                if (status == "failed")
                {
                    var summary = work.Value<string>("error_summary") ?? "Motion generation failed.";
                    throw new MotifectApiException(summary);
                }

                await Task.Delay(TimeSpan.FromSeconds(intervalSeconds), cancellationToken);
            }

            throw new MotifectApiException($"Timed out waiting for work {workId}.");
        }

        public async Task DownloadAsync(string url, string destPath, CancellationToken cancellationToken = default)
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            request.Headers.UserAgent.ParseAdd(DefaultUserAgent);
            request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("*/*"));

            using var response = await _http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            var body = await response.Content.ReadAsByteArrayAsync();
            if (!response.IsSuccessStatusCode)
            {
                var text = Encoding.UTF8.GetString(body);
                throw new MotifectApiException(
                    string.IsNullOrWhiteSpace(text) ? $"Download failed ({(int)response.StatusCode})" : text,
                    (int)response.StatusCode);
            }

            Directory.CreateDirectory(Path.GetDirectoryName(destPath) ?? ".");
            File.WriteAllBytes(destPath, body);
        }

        public async Task<JObject> GenerateAndExportAsync(
            string prompt,
            string destPath,
            string exportFormat,
            int durationSeconds,
            string modelKey,
            Action<JObject> onProgress = null,
            CancellationToken cancellationToken = default)
        {
            var workId = await GenerateAsync(prompt, durationSeconds, modelKey, cancellationToken);
            var work = await PollUntilCompleteAsync(workId, onProgress, cancellationToken: cancellationToken);

            var url = FindAssetUrl(work, exportFormat);
            if (string.IsNullOrEmpty(url))
            {
                work = await ConvertAsync(workId, exportFormat, cancellationToken);
                url = FindAssetUrl(work, exportFormat);
            }

            if (string.IsNullOrEmpty(url))
            {
                throw new MotifectApiException($"No {exportFormat.ToUpperInvariant()} export found for work {workId}.");
            }

            await DownloadAsync(url, destPath, cancellationToken);
            return work;
        }

        private async Task<JObject> RequestAsync(
            string method,
            string path,
            JObject body,
            CancellationToken cancellationToken)
        {
            using var request = new HttpRequestMessage(new HttpMethod(method), $"{_baseUrl}{path}");
            if (body != null)
            {
                request.Content = new StringContent(body.ToString(), Encoding.UTF8, "application/json");
            }

            using var response = await _http.SendAsync(request, cancellationToken);
            var text = await response.Content.ReadAsStringAsync();
            JObject payload;
            try
            {
                payload = string.IsNullOrWhiteSpace(text) ? new JObject() : JObject.Parse(text);
            }
            catch (Exception exc)
            {
                throw new MotifectApiException($"Invalid JSON response: {exc.Message}", (int)response.StatusCode, exc);
            }

            if (!response.IsSuccessStatusCode)
            {
                var message = payload.Value<string>("error")
                    ?? payload.Value<string>("detail")
                    ?? payload.Value<string>("title")
                    ?? text;
                throw new MotifectApiException(message, (int)response.StatusCode);
            }

            if (payload.Value<bool?>("ok") == false)
            {
                throw new MotifectApiException(payload.Value<string>("error") ?? "Unknown API error.");
            }

            return payload;
        }
    }
}
