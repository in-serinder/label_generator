# dtpweb 打印接口速查

> 依据《德佟电子-dtpweb（PC Web）打印接口快速入门 V2.1.20220627》
> 并结合 npm 包 `dtpweb`（本项目集成版本 `2.7.260720`，位于 `printer/web/lib/dtpweb.js`）整理。

## 1. 接口是什么

dtpweb 接口是德佟电子在「dtpweb 打印助手」之上封装的 JavaScript 接口。打印助手是运行在本机的
一个本地服务，浏览器中的 `dtpweb.js` 通过 HTTP 与之通信，再由助手把打印数据下发给标签打印机。

```
你的页面 (dtpweb.js)  ──HTTP──▶  dtpweb 打印助手(本机)  ──▶  德佟标签打印机
```

**特点**

- 兼容 Chrome / Firefox / Edge / IE 及 360、QQ、搜狗等第三方内核；
- 支持 Windows、麒麟 OS、统信 UOS、Ubuntu、Debian；
- 任何能发 HTTP 请求的语言都可以使用（本项目由 Python 通过浏览器桥接调用）；
- 官方推荐异步接口（`lib` 目录），`lib_sync` 为旧版同步兼容包。

## 2. 环境准备

| 系统 | 准备方式 |
| --- | --- |
| Windows | 安装德佟打印机驱动即可，驱动内置了 dtpweb 打印助手 |
| Linux / 其他 | 需单独安装 dtpweb 打印助手 |

本项目额外依赖 **Chrome 或 Edge**（用于承载运行 dtpweb.js 的页面），
由 `printer/chrome_bitmap.py` 中的 `find_chrome()` 自动查找。

## 3. 引入方式

### 3.1 浏览器 / 本地 HTML（本项目采用）

```html
<script type="text/javascript" src="./lib/dtpweb.js"></script>
<script>
  var api = dtpweb.getInstance();
</script>
```

UMD 包挂载的全局对象名为 `dtpweb`，导出 `DTPWeb`、`getInstance`、`checkServer`、
`LPA_Utils`、`LPA_JobNames` 等。

### 3.2 Vue / npm

```bash
npm install dtpweb   # 或 yarn add dtpweb
```

```js
import { DTPWeb, LPA_JobNames } from "dtpweb";

async mounted() {
  this.api = DTPWeb.getInstance();
  DTPWeb.checkServer((resp) => {
    if (resp.statusCode === 0) console.log("打印助手可用");
  });
}
```

## 4. 标准调用时序

```
DTPWeb.getInstance()
      │
      ▼
api.checkPlugin()         检测打印助手是否在运行
      │
      ▼
api.openPrinter(name)     连接打印机
      │
      ▼
api.startJob({w, h})      创建指定尺寸的标签任务
      │
      ▼
api.drawText / draw2DQRCode / drawRectangle ...   绘制内容
      │
      ▼
api.commitJob({copies})   提交任务，开始打印
      │
      ▼
api.closePrinter()        关闭打印机（参数会被保留）
```

最小可用示例（打印一段文本）：

```js
const api = dtpweb.getInstance();
api.checkPlugin((resp) => {
  if (resp.statusCode !== 0) return alert("未检测到打印助手");
  api.openPrinter({ name: "P2-Y6092210363" }, (ok) => {
    if (!ok) return;
    api.startJob({ width: 40, height: 30 });
    api.drawText({ text: "Hello", fontHeight: 3 });
    api.commitJob(() => api.closePrinter());
  });
});
```

## 5. 接口清单

### 5.1 初始化与检测

| 接口 | 说明 |
| --- | --- |
| `DTPWeb.getInstance(options?)` | 获取单实例接口对象 |
| `DTPWeb.checkServer(options?)` | 检测打印服务，支持 `{ callback }` |
| `api.checkPlugin(options?)` | 同上，`{ timeout, callback }` |
| `api.init(options)` / `setOptions(options)` | 初始化配置（字体、线宽、是否 JSON 模式等） |
| `api.getVersion(clientType?)` | 打印助手版本 |
| `api.getServerInfo(clientType?)` | 打印助手信息 |
| `api.getFontNames()` | 系统字体列表 |
| `api.setSupportedPrinters(names)` | 放行非德佟品牌打印机 |

`LPA_InitOptions` 常用字段：`fontName`、`fontHeight`、`lineWidth`、`radius`、`cornerWidth`、
`jsonMode`（默认 true）、`logLevel`、`https`、`recheck`、`checkFontName`、`supportedPrinters`。

### 5.2 打印机管理

| 接口 | 说明 |
| --- | --- |
| `api.getPrinters(options?, callback?)` | 获取打印机列表，常用 `{ onlyOnline, onlyLocal, onlySupported }` |
| `api.requestPrinters(options?)` | 同上的 `LPA_Response` 版本 |
| `api.getDeviceInfo(printerName)` | 指定打印机的设备信息 |
| `api.getDefaultPrinter()` / `setDefaultPrinter(name)` | 系统默认打印机读写 |
| `api.discoveryPrinters(mode?)` | 搜索局域网打印机，建议 2 秒后再取列表 |
| `api.getDeviceCacheList()` | 缓存的打印机列表 |
| `api.openPrinter(options?, callback?)` | 打开打印机，`{ name, ip, port, type }` |
| `api.closePrinter()` | 关闭打印机（未提交的数据会自动提交） |
| `api.getPrinterName()` | 当前已连接打印机名称 |
| `api.getPrinterWidthMM()` | 打印头宽度（未连接时返回 48） |
| `api.isPrinterOpened()` / `isPrinterOnline()` | 连接状态 / 在线状态 |
| `api.showProperty({ printerName, showDocument })` | 打开打印机属性或首选项界面 |
| `api.resetDevice(mode?)` | 重启打印机 |

### 5.3 打印任务

| 接口 | 说明 |
| --- | --- |
| `api.startJob(options)` | 创建任务。关键参数：`width`/`height`（毫米）、`orientation`（0/90/180/270）、`jobName`、`margin`/`marginH`/`marginV`、`offsetX`/`offsetY`、`printerDPI`、`printerWidth`、`gapType` |
| `api.abortJob()` | 取消当前任务（数据丢弃，参数保留） |
| `api.commitJob(options?, callback?)` | 提交打印。`copies`、`orientation`、`threshold`（默认 192）、`printSpeed`、`printDarkness`、`gapType` |
| `api.startPage()` / `endPage()` | 手动分页 |
| `api.getJobID()` / `getJobInfo(options)` | 任务标识与状态 |
| `api.getPageInfo()` / `getPageImage({ page })` | 获取页数与页面图片（预览用） |
| `api.print(jsonOptions, callback?)` | 直接以 JSON 描述整张标签并打印 |
| `api.printWdfx(options)` | 解析并打印 wdfx 文件 |

`jobName` 取 `LPA_JobNames` 时不会真正打印：

| 常量 | 值 | 用途 |
| --- | --- | --- |
| `LPA_JobNames.Preview` | `#!#Preview#!#` | 生成白底预览图 |
| `LPA_JobNames.Transparent` | `#!#Transparent#!#` | 生成透明底预览图 |
| `LPA_JobNames.Print` | `dtpweb` | 正常打印 |

### 5.4 绘制接口

| 接口 | 关键参数 |
| --- | --- |
| `drawText(options)` | `text`、`x`、`y`、`width`、`height`、`fontName`、`fontHeight`（毫米）、`fontStyle`、`autoReturn`、`charSpace`、`lineSpace`、`horizontalAlignment`、`verticalAlignment`、`orientation` |
| `measureText(options)` | 同 drawText 的字体参数，返回文本宽高与行数 |
| `draw1DBarcode(options)` | `text`、`type`、`textHeight`、`barPixels` 等 |
| `draw2DBarcode(options)` | 通用二维条码 |
| `draw2DQRCode(options)` | `text`、`x`、`y`、`width`、`height`、`eccLevel`、`qrcPixels`、`qrcVersion` |
| `draw2DPdf417(options)` | `text`、`eccLevel`、`p417Pixels` 等 |
| `draw2DDataMatrix(options)` | `text`、`symbolShape`、`minHeight`/`maxHeight` 等 |
| `draw2DGridMatrix` / `drawGridMatrix` | 网格码 |
| `drawRectangle(options)` | `x`、`y`、`width`、`height`、`lineWidth`、`fill` |
| `drawRoundRectangle(options)` | 另加 `cornerWidth`、`cornerHeight` |
| `drawEllipse(options)` | `x`、`y`、`width`、`height`、`lineWidth`、`fill` |
| `drawCircle(options)` | `x`、`y`、`radius`、`lineWidth`、`fill` |
| `drawLine(options)` | `x1`、`y1`、`x2`、`y2`、`lineWidth` |
| `drawDashLine(options)` | 另加 `dashLens` |
| `drawImage(options)` | `imageFile`（路径或 URL）、`x`、`y`、`width`、`height`、`threshold` |
| `drawImageD(options)` | `data`（base64 / ArrayBuffer / Blob）、`format`、`drawWidth`、`drawHeight` |
| `drawTable(options)` | `tableRows` / `cells`、`columnWidths`、`rowHeights`、`groups` 等 |
| `nextLine(lineHeight?)` | 返回下一个绘制位置的 Y 坐标 |

**单位说明：** 坐标、宽高、字体高度、线宽默认单位都是**毫米**；`region*` 一类参数是长度数组，
接口内部会转换成 0.01 毫米。位图的灰度阈值默认为 192（≥192 视为白）。

### 5.5 参数设置

| 接口 | 说明 |
| --- | --- |
| `api.getParam(id)` | 读取打印参数，`id` 见 `LPA_ParamID` |
| `api.setParam({ id, value })` | 修改打印参数 |
| `api.getGapType()` / `setGapType(v)` | 纸张类型 |
| `api.getPrintDarkness()` / `setPrintDarkness(v)` | 打印浓度 |
| `api.getPrintSpeed()` / `setPrintSpeed(v)` | 打印速度 |
| `api.getPrinterDPI()` | 打印机分辨率 |
| `api.getImageAlignment()` / `setImageAlignment(v)` | 图片打印对齐方式 |
| `api.setItemHorizontalAlignment` 等 | 已废弃，绘制时直接传对齐参数 |

`LPA_ParamID` 常用值：`GapType = 1`、`PrintDarkness = 2`、`PrintSpeed = 3`、
`PrinterDPIx = 4`、`PrinterDPIy = 5`、`ImageAlignment = 36`。

### 5.6 状态查询

| 接口 | 说明 |
| --- | --- |
| `api.isPrintable(full?)` | 打印机是否可打印 |
| `api.getDeviceStatus()` | 设备状态 |
| `api.getPrintStatus()` | 打印状态 |
| `api.getConsumable()` | 耗材信息 |
| `api.getNotifyInfoE()` | 通知信息 |
| `api.getBufferSize()` | 剩余缓存大小 |

### 5.7 工具函数

| 接口 | 说明 |
| --- | --- |
| `api.mm2Pound(v)` / `pound2Mm(v)` | 毫米与磅互转 |
| `api.mm2Pix(v, dpi?)` / `pix2Mm(v, dpi?)` | 毫米与像素互转（默认 203dpi） |
| `api.imageSrc2DataUrl(src, cb)` | 图片 URL 转 base64 |
| `DTPWeb.registerBarcode2DEncoder(encoder, type)` | 注册自定义二维码生成器 |

### 5.8 枚举速查

**LPA_GapType（纸张类型）**

| 值 | 含义 |
| --- | --- |
| 255 | 随打印机设置 |
| 0 | 连续纸（小票纸） |
| 1 | 定位孔（已废弃） |
| 2 | 间隙纸 |

**LPA_PrintSpeed（打印速度）**：`255` 随打印机，`0` 最慢，`1` 较慢，`2` 正常，`3` 较快，`4` 最快。

**LPA_PrintDarkness（打印浓度）**：`0`–`15`，数值越大越浓，`255` 表示随打印机设置。

**LPA_ItemAlignment（对齐方式）**：`0` 居左/居上，`1` 居中，`2` 居右/居下，`3` 拉伸，`4` 放大。

**LPA_FontStyle（字体样式）**：`0` 常规，`1` 粗体，`2` 斜体，`3` 粗斜体，`4` 下划线，`8` 删除线。

**LPA_AutoReturnMode（换行模式）**：`0` 不自动换行，`1` 按字换行（默认），`2` 按词换行。

## 6. 本项目中的集成方式

Python（tkinter）无法直接执行浏览器 JS，因此采用「临时 HTTP 服务 + 浏览器执行 + 结果回传」的桥接方案：

| 文件 | 职责 |
| --- | --- |
| `printer/web/print.html` | 浏览器端打印页面，调用 dtpweb 接口绘制并打印 |
| `printer/web/lib/dtpweb.js` | dtpweb 官方 UMD 接口包 |
| `printer/dtpweb_bridge.py` | 拼装 job.json、启动临时 HTTP 服务、拉起浏览器、等待结果 |
| `printer/chrome_bitmap.py` | 兜底通道：渲染位图交给 Chrome/Edge 打印（适用于任意品牌打印机） |

`job.json` 结构：

```json
{
  "printerName": "P2-Y6092210363",
  "paperWidth": 50.0,
  "paperHeight": 25.0,
  "orientation": 0,
  "copies": 1,
  "gapType": 255,
  "darkness": 255,
  "speed": 255,
  "jobName": "LabelGenerator",
  "items": [
    { "type": "text",   "text": "TYPE:", "x": 1.5, "y": 2.0, "fontHeight": 2.75, "fontStyle": 0, "fontName": "黑体" },
    { "type": "qrcode", "text": "TYPE:Resistor|PKG:0805|RNG:10K 1%", "x": 29.5, "y": 3.0, "size": 19.0 }
  ]
}
```

打印页支持两种动作：`?action=print`（打印标签）与 `?action=printers`（仅查询打印机列表）。

## 7. 常见问题

| 现象 | 排查方向 |
| --- | --- |
| 提示「未检测到打印助手」 | Windows 下安装德佟打印机驱动；其他系统单独安装打印助手；确认助手进程已启动 |
| 提示「打开打印机失败」 | 打印机名称是否正确、是否开机/在线；可先用 `?action=printers` 拉取真实名称 |
| 提示「等待打印结果超时」 | 浏览器被安全软件拦截、助手端口被防火墙占用，或打印机离线 |
| 只打印空白/内容偏移 | 检查 `startJob` 的 `width`/`height` 与实际标签纸是否一致，必要时调整 `offsetX`/`offsetY` |
| 二维码扫不出 | 标签过小或 `eccLevel` 太低，可增大二维码 `width` 或提高纠错等级 |
