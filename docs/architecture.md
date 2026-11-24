# 系统架构与分层

> 以主项目 `agent/PROJECT_FRAMEWORK.md`、`agent/INTERFACES.md`、`agent/CODE_CONVENTIONS.md` 为准，本页为展示摘要。
> 架构图见 [`../images/arch-overview.svg`](../images/arch-overview.svg)。

## 1. 分层与职责

| 层 | 目录 | 职责 | 不该做什么 |
|---|---|---|---|
| **应用 / UI** | `APP/ui/` | 屏幕、控件、主题、i18n、手势与状态机 | 不直接读写硬件寄存器、不直接调 BSP |
| **服务** | `APP/services/` | 统一 VFS、POSIX 层、OTA 客户端、日志、系统监控 | 不含 UI 逻辑 |
| **模型 / 网络** | `APP/model/`、`APP/net/` | 实体模型 + 事件总线（MVVM）；C6 桥接、MQTT 过滤器、Device Profile | 不直接碰显示 |
| **BSP / 驱动** | `Drivers/BSP/` | LTDC、触摸、SDRAM、QSPI、SDMMC、SPI、I2C 传感器、日志、TLSF | 不含业务语义 |
| **HAL / CMSIS** | `Drivers/STM32H7xx_HAL_Driver`、`Drivers/CMSIS` | ST 官方抽象（**不在应用层直接调用**，由 BSP 包装） | — |

**已登记的 5 处分层偏差**（`// LAYER-DEVIATION` 注释在代码里，如实记录而不是假装没有）：
GUI 任务直接调 BSP、模型层引用 LVGL、BSP 的日志组件反向调用 APP 的 VFS、net↔services 存在环等。
这类偏差都写了理由与收敛计划 —— **分层不是画图，是要能被 grep 检查的**。

## 2. 关键接口契约

### 2.1 桥接协议（STM32 ↔ ESP32-C6）

```
帧格式：AA55 | type | len | payload | CRC16
```

- **`type` 就是唯一契约**：路由与载荷格式由 type 隐含定义，**没有额外的 format 字节**。
- 系统命令 `0x10 ~ 0x17` 走**二进制结构体**（`bridge_sys_*_t`）；JSON 只留给握手 / 调试 / MQTT 透传。
- 为什么这么设计：单通道 UART 上，**"命令码决定一切"** 比"带 schema 的通用帧"更省字节、更好调试、更不易错。

主要命令码（摘要）：

| type | 方向 | 含义 |
|---|---|---|
| `0x01/0x02` | 双向 | 心跳 / 状态 |
| `0x03` | 下行 | 属性写入（走 Device Profile 字段映射） |
| `0x07/0x08` | 下行/上行 | OTA 下载请求 / 数据块 |
| `0x09` | 下行 | 日志级别 / 调试开关 |
| `0x20` | 上行 | OTA 自动触发（含 URL + sha256） |

### 2.2 统一 VFS

- 对上层只有**一套接口**（`vfs_open/read/write/seek/stat/...`），底下按盘符路由：`S:` → littlefs，`U:` → FatFs。
- **所有权模型**：FS 操作收敛到**单一工作线程 + 请求队列**，调用者不持锁、不阻塞在介质上。
- 内部原语层 `vfs_core.h` 约定**零日志调用** —— 目的是从设计上消掉"持 FS 锁打日志 × 日志 sink 调 FS"的
  双向等待环（这条在真机上抓到过一次死锁，Renode 因为没开文件 sink 反而测不到）。
- 上面还叠了 **POSIX/newlib 系统调用层**（`open/read/write/lseek` 直接可用），便于复用标准库与移植代码。

### 2.3 事件总线与实体模型

- 实体（灯 / 开关 / 空调 / 传感器…）统一抽象为 `entity_t`，UI 只订阅事件，不直接访问设备。
- 命令下发走契约 type，状态回读走事件 —— **UI 与设备解耦**，新增设备不改 UI 代码。
- 后期引入 **Device Profile（设备描述化）**：设备用 JSON 描述（字段映射 + 点分路径 + 属性池），
  上电加载并注册，避免每加一个设备就改一次 C 代码。

## 3. 并发模型

| 任务 | 优先级 | 职责 | 备注 |
|---|---|---|---|
| GUI | 2 | LVGL `lv_timer_handler` + flush | 与渲染线程通过 `lv_lock` 串行化 |
| MEDIA | 1 | （媒体分支）解码与上屏 | 默认构建不含 |
| FS_IO | 低 | 文件系统工作线程 | 单线程所有权，避免全局锁 |
| 其他 | 低 | 事件定时器、I2C 守护、SPI 守护、桥接 | 多为事件/队列驱动 |

**约定**：ISR 里只做"置标志 / 投队列 / 给信号量"，业务一律回任务上下文；
需要跨任务唤醒时**判据要用 `!= taskSCHEDULER_NOT_STARTED`**（因为 `== RUNNING` 在任何 `vTaskSuspendAll()` 窗口内都为假）。

## 4. 构建与测试

| 环节 | 内容 |
|---|---|
| 构建系统 | CMake + Ninja；`CMakePresets.json` 提供 `Debug` / `RelWithDebInfo` / 仿真档 |
| 双配置纪律 | 任何改动必须同时通过 `Debug` 与 `RelWithDebInfo` 编译 |
| 仿真 | Renode：启动 sentinel、驱动链路、SPI Flash 模型、FrameDump 导出显示帧 |
| 主机测试 | 可移植模块（VFS 请求队列、盘路由、demux 等）编成主机可执行 + ctest |
| CI | GitHub Actions 三配置构建 + "模拟器宏泄漏"守卫（生产 `.c` 出现仿真专用宏即红） |
| 产物 | `bin/hex` 由 `objcopy` 生成并记录 sha256（源码一动即作废，需重出） |

## 5. 为什么这些设计值得讲

1. **约束写在能被检查的地方**：分层偏差用 `LAYER-DEVIATION` 注释、模拟器隔离用 CI 守卫、
   接口契约用编译期宏与自检函数 —— 不靠"记得"。
2. **每个"规矩"背后都对应一次实际故障**：零日志的 VFS 内层对应 AB-BA 死锁；
   DMA 缓冲非缓存对应 IDMATE / 数据错；刷新计数重算对应撕裂。
3. **可观测性先行**：vblank 间隔用 1 MHz 时基量、欠载用逐帧计数、DMA 用状态快照 ——
   先把仪器做对，再谈优化。
