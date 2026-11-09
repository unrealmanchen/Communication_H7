# 哨兵底盘 · 七路串口工具

用于 RoboMaster 哨兵底盘联调的 Windows 串口工具：**7 路串口常开接收**，同时可按设定频率发送协议帧。接收端只按**帧头识别**统计接收成功，并记录每一路的接收成功时刻与接收频率，用于验证转发链路是否正常。

## 功能

**发送页**

- 7 路串口，每路独立选择串口、波特率（9600–2000000）、发送频率（0.1–1000 Hz）
- 每路独立发送开关；顶部“一键开启 / 一键关闭”
- 只要配置了 COM，端口就会**常开接收**；开关只控制是否周期发送
- 状态显示：未开启 / 打开中 / 已连接（只接收）/ 发送中（含实际频率）/ 异常
- 发送内容固定为 **0x402 底盘速度指令**测试包（x=1.5、y=0、z=0.5），自动计算 CRC8 / CRC16，每帧 22 字节。文档里的示例是 y=2.5，改动 y 即可复现示例帧

**接收记录页**

- 已指定 COM 的端口在任意时刻持续接收
- 分别统计并显示每路的**解析成功频率**、**总接收频率**、**解析错误次数和错误率（保留三位小数）**
- 顶部显示所有端口的**总错误率**
- 帧头（`A5 | 长度 | 00 | CRC8`）正确即计入总接收；数据收全且 CRC16 正确才算解析成功
- 解析错误（帧头 CRC8、长度非法、CRC16）会打印详细原因和**完整接收内容（HEX）**
- 接收记录支持按“成功 / 错误”筛选，筛选状态会保存
- **模式一 · 单端口**：只打印所选端口的解析成功/错误记录
- **模式二 · 全部端口**：打印全部 7 路的解析成功/错误记录
- 两种模式顶部都始终显示 7 路成功/总接收频率
- “错误清零”按钮：清零错误计数和错误率，并清空接收记录
- 接收记录页带**测试计时器**（时:分:秒.毫秒），并有“计时归零”按钮
- 不打印正常帧的包内容

**配置**

- 所有配置保存在程序目录的 `config.json`
- 修改后 500 ms 自动保存；关闭窗口保存窗口位置；重启自动恢复
- 重启时 `enabled=true` 的端口会自动恢复发送；所有已指定 COM 的端口自动打开接收

## 协议与成功判定

22 字节帧：

```
A5 | 0D 00 | 00 | D3 | cmd_lo cmd_hi | data[13] | crc16_lo crc16_hi
```

- `CRC8(init=0xFF)` 校验前 4 字节 → 固定 `D3`
- `CRC16(init=0xFFFF)` 校验 header + cmd + data，小端序
- 总接收：帧头 `A5` + 长度 + `0x00` + 正确 CRC8 即计一次
- 解析成功：收全 22 字节且 CRC16 正确；否则记录为解析错误
- 固定发送：`0x402 底盘速度指令`，data 为 `float x / float y / float z / 0x00` 共 13 字节

## 运行

虚拟环境已创建在 `D:\deepseek\.venv`（PySide6 6.12 + pyserial 3.5）。

```bat
cd /d D:\deepseek\serial_tool
run.bat
```

或：

```bat
D:\deepseek\.venv\Scripts\python.exe main.py
```

## 配置文件

首次启动自动生成 `config.json`：

```json
{
  "version": 4,
  "window": { "width": 1180, "height": 780, "x": null, "y": null, "maximized": false },
  "send": {
    "ports": [
      {
        "name": "端口 1",
        "device": "COM3",
        "baud": 115200,
        "rate_hz": 100.0,
        "enabled": false
      }
    ]
  },
  "receive": { "mode": "all", "single_port": 0 }
}
```

- `device` 为串口名，如 `COM3`；未选择时为空。
- `enabled=true` 的端口会在下次启动时自动开始发送。
- `receive.mode` 为 `all`（模式二）或 `single`（模式一），`single_port` 为 0–6。
- 删除 `config.json` 可恢复默认配置；文件损坏时程序使用默认值启动并在底部提示。

## 目录

```
serial_tool/
├─ main.py                 程序入口
├─ run.bat                 Windows 启动脚本
├─ config.json             外部配置（首次运行生成）
├─ core/
│  ├─ protocol.py          协议帧 / CRC
│  ├─ config_store.py      配置读写
│  ├─ contracts.py         数据结构（含 SuccessEvent）
│  ├─ serial_manager.py    七路串口引擎（常开接收 + 帧头成功计数）
│  └─ virtual_device.py    引擎自测用虚拟数据
├─ ui/
│  ├─ theme.py             深色主题
│  ├─ widgets.py           开关 / 状态灯 / 端口编号
│  ├─ send_page.py         发送页
│  ├─ receive_page.py      接收记录页
│  ├─ main_window.py       主窗口
│  └─ branding.py          程序图标
└─ tests/                  协议、配置、串口引擎测试
```

## 测试

```bat
cd /d D:\deepseek\serial_tool
D:\deepseek\.venv\Scripts\python.exe -m unittest tests.test_serial_manager tests.test_protocol tests.test_config -v
```

- 协议测试：文档示例帧逐字节一致、CRC、流式解析。
- 引擎测试：串口常开接收、开关只控制发送、帧头成功计数、频率统计、热更新、错误隔离、线程清理。
- 配置测试：读写往返、损坏回退、参数边界。
