# NOTICE — 第三方数据与署名

本仓库**作者原创的代码、脚本与 3D 模型**按 **MIT** 许可（见 [LICENSE](LICENSE)）。
下列第三方数据/素材各有自己的许可，**MIT 不覆盖它们**；再分发本仓库（含导出的模型）时请一并保留本节署名。

## 1. OpenStreetMap — ODbL 1.0

- 涉及文件：`ref/zsfz_osm.json`（Overpass 原始返回）、`ref/derived/osm_plan.json`（ENU 平面化）、
  `build/geo.json` 与 `build/foc-t2.blend` 里的道面 / 滑行道中线 / 机坪几何。
- 要求：署名 **“© OpenStreetMap contributors”**；这些**衍生数据库按 ODbL 1.0 共享**
  （<https://www.openstreetmap.org/copyright>）。
- 换句话说：MIT 只覆盖造型与脚本；OSM 衍生几何那部分是 ODbL，不能只当 MIT 用。

## 2. OurAirports — Public Domain

跑道端点、长度、标高、机场基准点（ARP）。无附加要求。

## 3. CAAC AIP ZSFZ 2P-1 — 仅内部量取，不入库

- 本仓库**不含** AIP 原图（PDF 页面）、其文本层，也不含标定后的矢量 `ref/derived/chart_enu.json`
  或任何航图渲染（`ref/derived/*.png`）——这些全部从版本库移除并加入 `.gitignore`；
- 仓库里只保留由这些内部量取结果**推导出来的模型坐标**：`build/geo.json`（道面/中线/T2 轮廓）、
  `build/t2_eave_sat.json`（r7 新檐口轮廓）、`build/roof.json`。

## 4. 新闻照片 — 已移除

早期本地参考用过两张带 “福州晚报 / FZ Evening News” 水印的航站楼内景照片
（`ref/photos/t2_1.jpg`、`t2_2.jpg`）。**版权不属于本项目，已从版本库移除**，
`ref/photos/*.jpg` 现在被 `.gitignore` 忽略，仓库里不含任何这类图片。

## 5. 没有 Asobo / 微软资产

仓库里没有 MSFS SDK 示例资产，也没有 Asobo 版权素材；`build/foc-t2.blend`、`build/geo.json`、
`build/roof.json` 全部由本仓库脚本生成。

## 6. 免责

非官方项目，与福州长乐国际机场、中国民用航空局、微软 / Asobo 均无关联。
模型是按公开资料做的**视觉重构**，**不得用于导航、飞行或任何真实运行用途**。
