# OTA 设计：契约、状态机与失败处置

> 以主项目 `agent/OTA_PLAN.md`、`agent/OTA_BOOTLOADER_API_V2_DRAFT.h`、`APP/services/ota/` 为准，本页为展示摘要。

## 1. 为什么是"双槽 + staging"而不是"原地升级"

| 方案 | 风险 | 结论 |
|---|---|---|
| 原地覆盖 App 槽 | 升级中断即变砖，无回退 | ❌ 不用 |
| 单槽 + 备份区 | 备份/恢复逻辑复杂，仍需两份空间 | 不划算 |
| **双槽（A/B）+ staging** | 新固件先落到独立区域并校验，通过后才切槽 | ✅ 采用 |

**关键点**：`active_slot` 由 bootloader 持有；App **不能**自己"切槽成功"，只能"写入 + 请求切槽"。
**校验不过就不切** —— 这是不变砖的根本保证。

## 2. 端到端链路

```
① 云端 MQTT(TLS) 推送触发        { urlA, urlB, size, sha256, force? }
② ESP32-C6 收到 → 0x20 上行给 STM32（带服务器地址与镜像信息）
③ STM32 自算目标槽：当前跑 A ⇒ 写 B
④ STM32 下发 0x07 让 C6 走 HTTP Range 下载（支持断点续传）
⑤ C6 分块 0x08 回传 → STM32 边收边写 SD（记录 acked 偏移）
⑥ 收完 → 擦 staging → 写 SPI Flash → 自校验（CRC/SHA）→ 写 boot 配置 → 重启
⑦ bootloader：staging READY → 再校验 → 擦目标槽 → 流式写入 → 逐块回读比对
       ├─ 通过 → 切 active_slot → 启动新固件 → confirm
       └─ 不通过 → readback DENY（by design 的安全拒绝）→ 回跳原槽
```

**分层的意义**：下载（C6，带 TLS/HTTP）与写入/校验（STM32）职责分离，
所以换服务器、换云厂商都不用改固件里的下载逻辑 —— URL 来自触发载荷，设备不硬编码地址。

## 3. 状态与失败处置

| 状态 | 含义 | 失败时 |
|---|---|---|
| `IDLE` | 无任务 | — |
| `DOWNLOADING` | 分段接收写入 SD | 断线可续传（`acked` 偏移）；服务器不支持 Range 则重头 |
| `STAGING` | 写 SPI Flash staging | 写失败/校验失败 → 清 staging，保持原槽 |
| `READY` | staging 完成待 bootloader 处理 | — |
| `SWITCHING` | bootloader 校验与切槽 | 校验失败 → `readback DENY` → 回跳原槽 |
| `CONFIRMED` | 新固件启动并确认 | 若未确认 → 下次启动回退（安全网） |

**已踩过的坑（都变成了设计）**：

1. **"全链成功却失败"**：bootloader 从 SPI Flash 读 staging 时会**偶发整块返回 `0x00`**，
   坏值被原样写进 QSPI 目标槽；而 `0x00` 落在已擦区，**不先擦就永久坏**。
   修法：写路径**有界重读同值** + **先擦本窗再写** + 读源头加固。
   判别技巧：`0x00` 只能被写进去、不可能被擦出来 ⇒ 出现全 0 就说明**源读坏了**。

2. **staging 布局改成"容量无关"**：`staging_base = flash_size − 0x402000`（运行时推导，不再硬编码 `0x800000`）。
   副作用是**与新 bootloader 不兼容** ⇒ 定 **`0x010500` 版本分界**：更旧的固件只允许 SWD 直刷。
   这是**刻意的代价**，不是 bug。

3. **触发帧载荷会超长**：云端触发里的 URL + sha256 可达 647 B，而早期 C6 的 MQTT 接收缓冲只有 512 B
   ⇒ **整帧被静默丢弃**。修法：缓冲扩到 1024 B + 载荷上限 768 B。

## 4. 安全现状（诚实说明）

| 项 | 现状 |
|---|---|
| 镜像完整性 | ✅ 镜像自包含 CRC/SHA，bootloader 校验 |
| 传输加密 | ✅ HTTPS（**自签证书**，演示环境放宽校验）+ MQTT over TLS |
| **发布者鉴别** | ❌ **未实施**：broker 无 ACL、触发载荷无签名 ⇒ **不能保证"只有授权方"能发升级** |
| 建议的分层方案 | L1 分凭据 + ACL（可立即做）/ L2 Ed25519 签名触发（C6 验签）/ L3 发布口 mTLS / L4 镜像签名 |

## 5. 实测记录

| 项 | 结果 |
|---|---|
| 真机 A↔B 双向切换 | ✅ 成功（`crc32=0xD52A5B95` 一轮） |
| 自动 OTA（云端触发 → 切槽） | ✅ 镜像 1,120,212 B 完整，`image slot check pc=0x90019A19` |
| 走公网自建服务端 | ✅ `acked=1,138,124` 后成功切 `active_slot=1` |
| 失败回跳 | ✅ 多次触发 `readback DENY` 并回跳原槽，**未变砖** |
