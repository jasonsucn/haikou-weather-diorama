# 项目暂停状态 · 恢复手册

> 暂停时间：2026-11-17 23:50（Asia/Shanghai）
> 状态：**已于 2026-11-18 08:05 恢复开发**（用户下达「继续」）。暂停期间的冻结内容见下；恢复记录见文末。

---

## 1. 一句话现状

App、服务端、真实和风天气数据、最终 GLB 资产均已完成并联调通过；**双击 `start.cmd` 即可运行**。剩余的是收尾质量项（见第 6 节），不影响当前可用性。

## 2. 冻结的决策（恢复后不要改）

- 布局：**V1**（圆形底座 Ø224、独立海甸岛、世纪大桥跨海）；密度按 V2 手法补足。
- 地标：世纪大桥、骑楼老街、钟楼、云洞图书馆、万绿园、火山口、海甸岛。
- 风格：Q 版玩具（圆角、马卡龙、暖光）。
- 动画优先级：**车流 / 渔船 / 飞鸟**；其余合格即可。
- 交互：点击地标 + 24h/7d 时间轴 + 昼夜 + 天气演示，四项全要。
- 音频：**默认开启**（首次交互解锁），可静音。
- 交付：本地网页 + `start.cmd`，桌面优先，移动端基础适配。
- 分工：Lead = PM/QA + 集成兜底；资产由 GPT-6.1-SOL 子代理完成；应用层由 Lead 兜底实现。

## 3. 最终资产（已冻结）

| 项 | 值 |
| --- | --- |
| 文件 | `assets/models/haikou_v1.glb` |
| 大小 | 5,435,812 bytes（5.18 MiB） |
| SHA-256 | `F7142A322E4C9CCC82A0985A4EDF51BB0BEED649C322FFB072EC9099F2DE829C` |
| 三角面 | 98,747 |
| 网格 / 材质 | 759 / 24 |
| 覆盖 | 陆地+沙岸 48.705% |
| 街块 / 树 | 54 旧城+北侧街块；28 椰树 + 52 乔木 = 80 树 |
| 命名锚点 | 63 / 63；`Sea`、`Foam`、`Car_01..06`、`Boat_01..09`、`Cloud_1..3`、`Palm_01..28`、`ClockTower`、`Library`、`Park`、`Volcano`、`Haidian`、`Arcade_01..08`、`Bridge_Tower_L/R` |
| 统计 | `data/asset/stats.json`；浏览器 GLTFLoader 终验 PASS（98,747 tri / 24 mat / missing[]） |

> GLB 已包含最终铜牌外移、54 街块、80 树、平台支撑、6 组海浪线等收尾。子代理明确“模型不会再改”。Blender 四张 64samples 预览图可能未全部跑完，但 **GLB 与 stats 为准**；若 `data/asset/preview-*.png` 时间戳不一致，不要当作最终验收依据。

## 4. 当前可运行状态

- `server.mjs`：静态服务 + QWeather 代理 + 10 分钟缓存 + 快照降级；KEY 仅在服务端。
- `app/`：Three.js 场景、GLB 加载、静态网格按材质合并、动画组重建、天气效果、时间轴、地标卡、昼夜、演示、程序化音效。
- 最近一次 QA（2026-11-17 23:49，无头 Chromium / 软件渲染）：
  - 页面加载、真实/缓存降级 HUD、时间轴、地标卡、昼夜、雨天粒子均通过。
  - draw calls 约 182；FPS 20（软件渲染，不代表真实 GPU）。
  - 音频：`?audio=1` 显示解锁链路 `locked → running`（听感未验证）。
  - 移动端：390×844 iframe 布局截图通过（未真机触摸）。

## 5. 暂停前最后改动（恢复时需知道）

1. **动画骨架重建**：最终 GLB 导出时层级被拍平（Car_01/Boat_01/Palm_01 等无子节点），旧动画会只动车身/船体、掉零件。暂停前已在 `app/src/city.js` 增加按编号重新组装 `THREE.Group` 的逻辑，并按子代理给的桥轴 `(0.9205, 0, 0.3907)` 让车沿桥面移动。
   **恢复第一件事：近距离复核车/船/椰树是否整体移动且不脱节、不越出桥面。**
2. **昼夜兜底修复**：`applyLighting` 在 astro 缺失时（缓存降级）会把白天误判成夜晚，已改为 `6.8/18.2` 默认值。
3. **鸟类缩小**、云材质改 Basic 白、雨丝加密、地标卡打开时隐藏天气卡、移动端顶栏/地标横向滚动已修。

## 6. 恢复后的待办（按优先级）

### P0（恢复后第一轮）
- 近景复核车流方向：桥中心约 `(-35.5, 12.8, -45.5)`（glTF Y-up），长轴 `(0.9205, 0, 0.3907)`，两车道 ±1.8；确认 Car 组整体沿桥、不过界、不掉轮子。
- 复核渔船起伏/巡航、椰树摆动、云漂移是否整体运动（不再有“零件留在原地”）。
- 若发现脱节：优先在 `city.js` 的 `buildRigGroups` 收紧编号正则/组原点，不要改资产命名。

### P1
- 音频听感验证（雨声/海浪/鸟/雷），必要时调增益；听感无法在无头浏览器验证。
- 真实 GPU 上的 FPS 测试（当前 20fps 是 SwiftShader；draw calls ~182）。
- 移动端真机触摸验证（旋转/缩放/地标条滚动）。
- 白天云偏灰、雨天天空偏亮：调 `effects.js` 云材质/雾/天空 uniform。
- 等待并核对 4 张 64samples 预览图；同步 `docs/asset-report.md`。

### P2
- 灯塔光束、桥索灯带、更明显的水面反射/涟漪。
- 轻度 Bloom / 移轴景深（注意性能）。
- 地标卡与天气卡的信息去重。

## 7. 如何继续

```powershell
# 1) 读本文件 + README.md + docs/app-report.md
# 2) 启动
start.cmd        # 或 node server.mjs
# 3) 数据自检
node tools/qweather-probe.mjs
# 4) 调试参数
#    /?wx=rain|thunder|fog|night|sunny   /?fps=1   /?audio=1
#    app/mobile-preview.html            390×844 预览
# 5) 资产重建（可选，模型已冻结，不建议先跑）
& 'D:\DeepSeek Harness WorkSpace\blender-bridge\blender\blender-5.2.3-windows-x64\blender.exe' `
  --background --factory-startup --python tools/blender/build_haikou_v1.py
```

## 8. 凭据与安全

- `.env.qweather` 保存在工作区，已加入 `.gitignore`，**不要提交/外发**。
- API Host：`xxxxxxxx.qweatherapi.com`；开发者 ID / 凭据 ID / KEY 在 `.env.qweather` 与用户处。
- 如项目要交付他人，先轮换 KEY，或改为服务端 JWT。

## 9. 文件清单（关键）

```
start.cmd / server.mjs
app/{index.html,styles.css,mobile-preview.html,src/{main,city,effects,ui,sound}.js}
assets/models/haikou_v1.glb
data/asset/{stats.json,preview-*.png,density.png,_haikou_v1.blend}
data/app/{overview,rain,night,landmark,mobile}.png
tools/blender/build_haikou_v1.py
tools/qweather-probe.mjs
docs/{report-v1,app-report,asset-report,PAUSE-STATE}.md
vendor/three.module.min.js + three.core.min.js + addons/
```

## 10. 恢复检查清单（打勾再继续开发）

- [ ] 读 PAUSE-STATE / README / app-report
- [ ] start.cmd 能起、HUD 有真实数据（或缓存标记）
- [ ] 近景确认车/船/树/云整体动画
- [ ] 时间轴、昼夜、地标卡、演示正常
- [ ] 记下新发现的问题，按 P0→P2 排期


---

## 11. 恢复记录（2026-11-18）

- 服务恢复：`node server.mjs`；真实数据 24.5°C 少云 / 湿度 89% / 风 3.5 m/s / AQI 22。
- P0 通过：最终 GLB 拍平层级已在 `city.js` 重新组装为 Car/Boat/Palm/Cloud 组；车流改为沿桥中心 `(-35.5, ~13.9, -45.5)` + 桥轴 `(0.9205,0,0.3907)` 两车道 ±1.8 运动；近景截图确认车在桥面内、整车移动。
- 修复：astro 缺失时的昼夜误判（缓存降级会变黑夜）；雨天天空/雾/曝光过亮（wetSky 放大）；云改 Basic 白；鸟缩小抬高。
- 验收截图已更新：`data/app/overview|rain|night|landmark.png`。
- 仍待：音频听感、真实 GPU FPS、移动端真机触摸；白天云偏“棉花糖”、灯塔光束/Bloom 为 P2。
