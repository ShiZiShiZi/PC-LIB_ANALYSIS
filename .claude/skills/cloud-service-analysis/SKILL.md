---
name: cloud-service-analysis
description: Flag whether a PC library or application depends on third-party cloud services — login/auth, cloud storage, cloud database, cloud functions, push/messaging, analytics, crash reporting, remote config, maps, cloud AI, ads — and infer the cloud vendor (Firebase/AWS/GCP/Azure/Aliyun/Tencent/Supabase/Sentry…), by synthesizing the already-computed dependencies / runtime_surface.network / native_api.dynamic_libraries / function_summary blocks. Use for dimension 11 of PC library/application analysis. Model synthesis; feeds dim-9.
---

# Cloud service involvement — 云服务厂商推测 (model synthesis)

A focused lens that answers **"是否涉及云端服务？涉及哪家厂商？"**. 端侧 SDK（Firebase 登录/云存储、
AWS/GCP/Azure、Sentry 崩溃上报、各家 Analytics/推送）意味着运行期依赖第三方云后端——这对鸿蒙化评估
关键（需网络权限、厂商原生 SDK 未必在鸿蒙 PC 可用）。**职责分工**：本维度只标"是否涉及 + 哪家厂商 +
什么用途 + 置信"，**不**下移植结论（那是 dim-9，本维度只把信号喂过去）。

## 主旨与原则

**输出契约（下方 Output）是唯一硬约束。** 推荐厂商集（google_firebase/aws/gcp/azure/…）与用途集
（auth/cloud_storage/…）是**起点而非封闭清单**——遇到别的云厂商或用途，照常 coin 一个简短小写值标出，
并记入 `meta.observations`。确有云端后端但推不准是哪家 → `vendor:"unknown"` + `confidence:"low"`，别臆断。

**这是综合维度，不要重扫源码。** 复用本次分析**已算出**的：
- `dependencies`（厂商 SDK 包名：`firebase-*`/`boto3`/`@aws-sdk/*`/`google-cloud-*`/`@azure/*`/`@sentry/*`…）
- `runtime_surface.network`（硬编码 host/域名/endpoint：`*.firebaseio.com`/`amazonaws.com`/`sentry.io`…）
- `native_api.dynamic_libraries`（厂商动态库）
- `function_summary`（README/能力分类里"登录/云同步/在线备份/遥测上报"之类的定性）
按厂商归纳，引用它们的 `evidence`（file:line）即可，必要时再点开一两个关键 manifest/网络代码确认。

**生产代码口径**：只统计库自身**生产代码**触及的云用途，排除测试/示例/demo（与其它维度一致）。
一个只在 `examples/`、`tests/` 里连接的云 API 不进结论。

## 输出契约（Output，fills report `cloud_services`）

```json
{
  "present": true,
  "summary": "中文：本项目涉及的云端服务与厂商概览（不涉及则说明并 present:false）",
  "services": [
    {
      "vendor": "google_firebase",
      "categories": ["auth", "cloud_storage", "analytics"],
      "confidence": "high",
      "via": ["firebase-auth", "com.google.firebase:firebase-storage"],
      "endpoints": ["firebaseio.com", "firebasestorage.googleapis.com"],
      "evidence": ["app/build.gradle:42", "src/net.py:88"]
    },
    {
      "vendor": "sentry",
      "categories": ["crash_reporting"],
      "confidence": "high",
      "via": ["@sentry/electron"],
      "endpoints": ["sentry.io"],
      "evidence": ["package.json:31"]
    }
  ]
}
```

- `present`/`confidence` 是**闭轴**（`confidence` ∈ high/medium/low）；`vendor`/`categories`/`via`/`endpoints` 开放。
- 不涉及云端时 `present:false`，`services` 可为 `[]`；纯本地/离线库如实标注。

## 思路（Approach，可调整）

1. **从 dependencies 认厂商 SDK**：扫 `dependencies[].name` 里的厂商 SDK 包 → 定 `vendor` + `categories`
   （包名常自带用途，如 `firebase-auth`→auth、`firebase-storage`→cloud_storage、`@aws-sdk/client-s3`→cloud_storage）。
   `confidence:"high"`。
2. **从 runtime_surface.network 反推**：`network` 里硬编码的 host/域名映射到厂商
   （`*.googleapis.com`/`*.firebaseio.com`→google_firebase/gcp、`*.amazonaws.com`→aws、`*.azure.com`→azure、
   `*.aliyuncs.com`→alibaba_cloud、`*.myqcloud.com`→tencent_cloud、`sentry.io`→sentry、`*.supabase.co`→supabase）。
   仅凭域名/间接线索 → `confidence:"medium"/"low"`。
3. **从 native_api.dynamic_libraries** 认厂商动态库（较少见，多在移动/桌面混合 SDK）。
4. **归并去重**：同一厂商的多个 SDK/域名合成一条 `service`，`categories` 汇总，`via`/`endpoints`/`evidence` 并列。
5. **置信取值**：厂商 SDK 包名明确=high；仅硬编码域名或功能描述间接推断=medium；线索薄弱/厂商不定=low。

## 常见情形（recall aids，非穷举）

按厂商列 SDK 包名 / 域名线索：
- **Firebase(Google)** `google_firebase`：`firebase*`、`firebase-admin`、`com.google.firebase:*`、`@react-native-firebase/*`；
  域名 `*.firebaseio.com`/`*.firebaseapp.com`/`firebasestorage.googleapis.com`/`fcm.googleapis.com`。用途 auth/cloud_storage/database/analytics/push/crash_reporting/remote_config。
- **AWS** `aws`：`boto3`/`botocore`、`aws-sdk`/`@aws-sdk/*`、`aws-amplify`、Java `software.amazon.awssdk:*`；域名 `*.amazonaws.com`。
- **GCP** `gcp`：`google-cloud-*`/`@google-cloud/*`、`google-api-python-client`；域名 `*.googleapis.com`/`storage.googleapis.com`。
- **Azure** `azure`：`azure-*`/`@azure/*`、`Microsoft.Azure.*`；域名 `*.azure.com`/`*.windows.net`/`*.azurewebsites.net`。
- **阿里云** `alibaba_cloud`：`aliyun-*`/`aliyun-python-sdk-*`/`@alicloud/*`；域名 `*.aliyuncs.com`。
- **腾讯云** `tencent_cloud`：`tencentcloud-sdk-*`/`cos-python-sdk`；域名 `*.myqcloud.com`/`*.tencentcloudapi.com`。
- **华为云** `huawei_cloud`：`huaweicloud-*`/AGConnect；域名 `*.myhuaweicloud.com`/`*.hicloud.com`。
- **Supabase** `supabase`：`supabase`/`@supabase/supabase-js`；域名 `*.supabase.co`。
- **Sentry** `sentry`：`sentry-sdk`/`@sentry/*`/`sentry-native`；域名 `*.sentry.io`。用途 crash_reporting。
- 其它常见：Cloudflare(`cloudflare`,`*.cloudflare.com`,`*.workers.dev`)、Mapbox/Google Maps(maps)、
  Mixpanel/Amplitude/Segment/Google Analytics(analytics)、OneSignal/Pusher(push/messaging)、
  OpenAI/各家云推理(`ml_ai`)。

## 自我发现（反哺）

清单外的厂商/用途或拿不准的归类 → 在 `meta.observations` 记
`{dimension:"cloud_services", field, kind, value, rationale}`，供人工评审是否纳入推荐集。
