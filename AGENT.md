# AGENT.md — 给接手这个仓库的 AI / 人看的作业手册

福州长乐国际机场 **ZSFZ** T2 航站楼 + 滑行道，Blender 工程，目标是 MSFS 2024 地景。
本文件是**合同**：先读完再动手。数值以 `spec.py` 为准，叙事以 `README.md` 为准，验收以
`out/manifest.json` 里的回执为准。三者冲突时按这个顺序：`spec.py` > `manifest.json` > `README.md`。

---

## 0. 一句话现状（r6）

`build/foc-t2.blend` 是主交付物：93 个 mesh / 22,693 三角面 / 8 材质 / 5 机位。
T2 屋面是 **1.40 m 等厚薄弯板**（距离场高度场 + 竖直偏移 + 檐口封边），脊高 **39.70 m**，
幕墙内收 3 m、屋面外挑 8 m。`audit_mesh` 三件（roof / podium / glass）**pass**。
**MSFS / glTF 导出故意延后到 r7**，`out/archive/` 里的 r5 GLB 不是当前模型。

---

## 1. 目录与职责

| 路径 | 是什么 | 能不能手改 |
|---|---|---|
| `spec.py` | 冻结规格：原点、跑道、T2 高度层级、屋面参数、门、禁用项 | 只能按决策改，改完要同步 README/manifest |
| `tools/build_geo.py` | OSM + AIP 图 → `build/geo.json`（道面分块、滑行道中线、T2 轮廓/分体） | 可以 |
| `tools/build_roof.py` | 距离场 → 等厚薄板网格 → `build/roof.json`（含截面探针） | 可以，**必须**保持“单值高度场 + 竖直偏移”两个不变量 |
| `build_scene.py` | 读 geo/roof.json → 建 `build/foc-t2.blend` + 机位 + 视口设置 | 可以 |
| `tools/qc_render_r6.py` | 用 .blend 里的 5 个机位出 `out/renders/r6_cam-*.png` | 可以 |
| `out/manifest.json` | 交付清单 + 门回执 + 限制 + `.blend` 的 md5 | 每次重建都要刷新 md5 |
| `build/*.json` | 中间产物，**可删可重建**，不要手改数值 | 否 |
| `ref/derived/chart_enu.json`、`osm_plan.json` | 校准后的 AIP 图矢量 / OSM ENU 平面数据，`build_geo.py` 的输入 | 不要手改 |
| `ref/sat/`、`ref/apron/`、`tools/pylib*/` | 卫星瓦片 / AIP 原图矢量 / 第三方 python 库 | **不进仓库**（`.gitignore`） |

---

## 2. 环境（踩过的坑，别再踩）

1. **只有 Blender 自带的 Python 3.13 能跑几何脚本**：`tools/pylib313/` 是 cp313 的 shapely 2.2.0 + numpy；
   `tools/pylib/` 里的 cp312 版本在 Blender 里会报 `No module named 'shapely.lib'`（系统 python 3.15 也不行）。
   ```powershell
   blender -b -P tools\run_geo_roof.py    # build_geo.py + build_roof.py（内部按 __file__ 定位，任意 cwd 可跑）
   ```
2. 脚本里的路径一律**从 `__file__` 推导**（`ROOT`/`_ROOT`），不要写死盘符 —— 这个工程从
   `F:\dshproj\foc-t2` 搬到 `F:\foc_t2_msfs` 过一次，写死路径全废。
3. 写文件用 **UTF-8 无 BOM**。PowerShell 的 `Set-Content -Encoding utf8` 会加 BOM，Python 会报
   `SyntaxError: invalid non-printable character U+FEFF`；用 `.NET` 的 `UTF8Encoding($false)`。
4. 无头 Blender 里**别用 context 相关 `bpy.ops`**（`clip_start` 之外的 view3d ops、`mesh.*` 编辑操作等），
   优先 `bpy.data` / `bmesh` / `from_pydata`。
5. 长输出会被工具截断：看回执里的 `verdict` / `counts` / `md5`，别指望读完整日志。

---

## 3. 标准流水线（改完必须全跑一遍）

```powershell
# 1) 几何（改过轮廓/道面/屋面参数才需要）
blender -b -P tools\run_geo_roof.py

# 2) 场景（任何 build_scene.py / roof.json 改动都要跑）
blender -b -P build_scene.py

# 3) 验收：三件闭合体必须 pass（0 开边 / 0 非流形 / 0 退化 / 0 自交 / 逐壳法线朝外）
#    用 DSH 的 blender 插件：blender_rt_plan(op="audit_mesh", args={"objects": [...], "self_intersect": true})
#    或自带 python 复核：面积×板厚 = 有符号体积（277,102 m³ / 197,931 m² = 1.4000 m）

# 4) 出图（同机位，5 张）
blender -b build\foc-t2.blend -P tools\qc_render_r6.py

# 5) 刷新 out/manifest.json 里的 blend md5 / bytes，然后提交
git add -A; git commit -m "..."; git push
```

**Definition of done（一次改动算完成的条件，缺一不算）**：
① `audit_mesh` verdict=pass（不是 `degraded`、不是只看 `ok`）；
② 有数字：bbox/尺寸、板厚、脊高、tri 数、md5；
③ 有图：至少 `r6_cam-iso` + `r6_cam-section`（截面剪影是屋面的关键判据）；
④ `out/manifest.json` 更新；⑤ git 提交。

---

## 4. 不变量（改了就是返工）

| 不变量 | 数值 / 规则 | 为什么 |
|---|---|---|
| 坐标系 | 米制，原点 = ARP 25.929254N / 119.672524E，+X 东 +Y 北 +Z 上 | MSFS 摆放靠这个 |
| 屋面几何 | 高度场单值 `z=f(x,y)`，**竖直**下移偏移得到下表面，檐口封边 | 竖直偏移保证上下两张单值面永不相交；沿法线偏移会在凹角自交（r5 实测 18–23 处） |
| 板厚 / 脊高 | 1.40 m / 39.70 m（檐口 27.35，下沿 25.95） | 与照片截面、公开高度一致 |
| 檐口轮廓 | 用真实轮廓多边形**逐单元裁剪**，交点 1 mm 内焊接 | 保证檐口线精确、无 T 型接缝 |
| 道面分块 | 互不重叠（跑道/滑行道/机坪/地面用 shapely 相减），**多边形必须带洞导出** | 丢洞 = 机坪盖回滑行道 = 同 z 共面重叠 = z-fighting |
| 层间最小高差 | ≥ 0.30 m（视口 clip 1 m/80 km 时 1 km 处深度精度 ~0.09 m） | 小于这个值远看必打架 |
| 视口 clip | 每个 View3D 都写 clip 1 m / 80 km，并把视点停在 T2 | 工厂默认 0.1/1000 m 会把 4.4 km 的模型切一半 |
| 材质 | 纯色 PBR，无贴图（r6） | 贴图/UV 留到 r7 之后 |
| 单位/命名 | 对象前缀 `GEO-` / `MK-`；集合 `COL_Ground`/`COL_Geo`/`COL_Markings`/`COL_Cam` | 导出与装配按前缀筛 |

**禁用**：对 T2 壳体做布尔；用缩放的环代替真正的偏移；把带洞多边形只写外环；在没跑门的情况下交付。

---

## 5. 现在的已知缺口（按优先级）

1. **道面覆盖有洞**：OSM 的 apron/taxiway 多边形之间没铺满，地形底板会从缝里露出来（绿色）。
   导出前要么补面，要么按 MSFS 的 Projected Mesh 分层解决。
2. **光伏采光带缺失**：r5 的 `GEO-T2-pv` 是平面四边形，在旧厚屋面里其实埋在板内；新曲面下必须
   按松弛后的高度场重做成贴合面片（不能在 `build_scene.py` 里用解析场算，会和成品网格错开）。
3. **细节层**：檐口格栅/镂空板、幕墙竖挺、登机桥（每指廊 6–8 座）、陆侧雨棚、屋顶设备。
4. **实地照片**：见 README「后续计划」——拿到现场照片后按“同机位对照”的方式逐项校形。
5. **r7 导出**：`tools/export_glb.py`（glTF Y-up）+ `tools/verify_glb.py`（回读比对 bbox），
   之后再做 MSFS 工程（Projected Mesh / 材质 / LOD / 碰撞）。

---

## 6. 数据许可（对外发布前必读）

**本仓库已开源**：作者原创的代码与模型 = **MIT**（`LICENSE`）；第三方数据各有许可，逐项见 `NOTICE.md`。

| 数据 | 许可 | 要求 |
|---|---|---|
| **OSM**（滑行道中线、机坪多边形、跑道端点） | **ODbL 1.0** | 署名 “© OpenStreetMap contributors”，衍生数据库按 ODbL 共享。`build/geo.json`、`out/manifest.json`、导出的模型都含 OSM 派生几何 —— **MIT 不覆盖这部分** |
| **OurAirports**（跑道长度/标高/ARP） | Public Domain | 无 |
| **CAAC AIP 2P-1 图** | 仅内部量取 | 原图、PDF 文本层、**标定后的矢量 `ref/derived/chart_enu.json`**、以及所有航图渲染图**都不入库**；仓库只有由它们推出的模型坐标（`build/*.json`） |
| **新闻照片** | 版权不属于本项目 | 曾用的两张带“福州晚报”水印的照片**已从版本库移除**；今后 `ref/photos/` 只放确认可再分发的图，并登记到 `NOTICE.md` |
| 本仓库脚本与模型 | **MIT** | 保留版权与许可声明；导出物再分发时一并保留 `NOTICE.md` 的全部署名 |

**任何时候都不要**把下面这些提交上去（全部已在 `.gitignore` 里）：

- **任何参考图像**：卫星瓦片（`ref/sat/`）、航图渲染（`ref/derived/*.png`）、新闻/实拍照片（`ref/photos/*.jpg`）；
- **AIP 资料**：原图、PDF 文本层（`ref/pdf1/`、`ref/pdf2/`）、标定后的矢量（`ref/derived/chart_enu.json`）、逐要素导出（`ref/derived/feat_*`）；
- `tools/pylib*`（约 300 MB 第三方库）、`.credentials` 类文件。

提交前用 `git status --short` + `git check-ignore -v <path>` 自查；要入库的只能是**代码、模型、以及由参考数据推导出的坐标 JSON**。

---

## 7. 交互约定（和人协作时）

- 用户会**直接看图**判定“像不像”。任何形体结论都要给：同机位渲染图 + 关键尺寸数字，缺一不接受。
- 不确定就问，但**不要问已经写在 spec/manifest 里的数**。
- 每次改动都留一个可回退点：`.blend` 由 `build_scene.py` 全量重建，所以“回退”= 改回脚本参数再重建；
  纯手工改动一定要单独存 `.blend`/提交，别覆盖 `build/foc-t2.blend`。
- 报告用中文；代码注释中英混排可以，但**代码里不要写中文标点做分隔符**（易触发编码问题）。
