# 海口 V1 微缩城市资产报告

## 统计

- GLB: `assets/models/haikou_v1.glb` (5.31 MiB / 5572076 bytes)
- 三角面: 105,793
- 导出网格对象: 840
- 材质: 24 / 上限 24 (brick, butter, cloud, coral, cream, dark, foam, glass, gold, grass, lava, leaf, meadow, mint, road, sand, sea, skyblue, terracotta, trunk, white, window, wood, wood_dark)
- 场景范围 (Blender Z-up): X -112.0..112.0, Y -113.1..112.0, Z -6.9..53.7；GLB 按 Y-up 导出。
- 规范锚点: 63 / 63 已找到
- 缺失锚点: 无
- 旧城街块: 7；椰树: 28；乔木: 52；渔船: 9；帆船: 3
- 陆地与沙岸平面覆盖: 48.70% (由真实外轮廓面积计算)
- 旋转/缩放未应用对象: 无
- 统计清单: `data/asset/stats.json`；可复查源场景: `data/asset/_haikou_v1.blend`。

## 命名清单

- 动画锚点: `Sea`, `Foam`, `Car_01..Car_06`, `Boat_01..Boat_09`, `Cloud_1..Cloud_3`
- 地标: `ClockTower`, `Bridge_Tower_L`, `Bridge_Tower_R`, `Library`, `Park`, `Volcano`, `Haidian`
- 骑楼: `Arcade_01..Arcade_08`
- 椰树: `Palm_01..Palm_28`
- 主构成: `MainIsland`, `Shore_Sand`, `Bridge_Deck`, `Lighthouse`, `Sail_01..Sail_03`

## 渲染

- Blender: 5.2.3 headless; Cycles CPU; 1400x900; 64 samples; AgX; denoising enabled.
- 预览: `data/asset/preview-main.png`, `preview-bridge.png`, `preview-oldtown.png`, `density.png`.
- 主视角: 西南 3/4，30.1 度俯视；密度图为统一灰模正交俯视白底。
- 已实际运行 3 轮 900x600 / Cycles 24 samples blockout 并查看 PNG，保留 `_blockout-r1..r4.png` / `_density-r1..r4.png` 作为过程审查证据；一次性脚本与 `.blend1` 备份已清理，正式渲染为 `preview-*.png` / `density.png`。
- 根据图像修正了码头接岸、骑楼柱廊高度、火山真凹口、图书馆三独立洞口、铜牌表面位置、北侧密度与木纹。

## 已知问题

- 城市细节为程序化 Q 版几何，店招没有可读的逐店文字，钟面仅含指针。
- 车、船、云、椰树已提供准确命名锚点，动画由 App 驱动；GLB 本身不含烘焙动画。
- 火山口以几何凹碗表达，未包含粒子烟雾或动态熔岩。
- 海面外圈保留船行水域；近岸以三组渔港、防波堤、游憩栈桥、帆船、航标、浅海带和浪线形成层次。
- 预览缩小到手机尺寸时，店招、钟针和图书馆洞口的细节依赖特写查看。
- 本机沙箱日志：`Extensions: writing cache failed ([WinError 5] 拒绝访问。: 'C:\Users\17600\AppData\Roaming\Blender Foundation')`。
- 保存源场景时 OpenImageIO 对 `C:\Users\17600\.thumbnails\large` 的缩略图缓存写入被拒；工作区中的 GLB、源场景与 PNG 正常保存。
