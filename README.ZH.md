# DriveMind

[日本語](README.md) / [English](README.EN.md) / [中文](README.ZH.md) / [한국어](README.KR.md)

**DriveMind** 是面向 Windows 的磁盘信息查看、容量确认、文件夹结构思维导图生成工具。它可以显示内部磁盘、外部磁盘、分区、盘符和卷标，并将选中的驱动器导出为 DesktopNaotu 可用的 `.km` 文件。

> 版本：`v2.0.0`  
> 作者：[@S2OUnicus](https://github.com/S2OUnicus)  
> 项目：<https://github.com/S2OUnicus/DriveMind>  
> 许可证：CC BY-NC-ND 4.0

![DriveMind 主界面](docs/screenshots/1_Index.png)

## 可以做什么

- 显示已连接的磁盘、分区、盘符、卷标、文件系统和属性。
- 分别显示内部磁盘和外部磁盘的容量总计。
- 通过进度条显示已用容量、使用率、剩余容量和总容量。
- 为每个分区设置分组、用途和备注。
- 为分组设置颜色，并显示在主界面的分组列。
- 将选中的驱动器导出为 DesktopNaotu 用 `.km` 思维导图。
- 使用 DesktopNaotu 打开生成的 `.km` 文件。
- 在分区信息窗口查看容量、属性、使用率和文件类型分析。
- 按分类打开文件列表，支持分页和按大小排序。
- 设置是否显示 RAM 磁盘、WebDisk、网络驱动器和特殊分区。
- GUI 支持日语、英语、中文和韩语切换。
- 支持 darkmode / lightmode 切换。
- 从 GitHub Releases 检查新版本。

## 启动开发版

需要 Python 3.10 或更高版本。在仓库目录中执行：

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m drivemind
```

Windows 也可以使用：

```text
scripts/run_dev.bat
scripts/run_dev.ps1
```

PyInstaller 打包示例：

```powershell
pyinstaller --onefile --noconsole --name DriveMind --icon=src\drivemind\assets\logo.ico --paths src src\drivemind\__main__.py
```

生成的程序通常位于 `dist\DriveMind.exe`。

## 主界面

上半部分是磁盘和分区列表，下半部分是容量总计和功能按钮。物理磁盘作为父项显示，分区作为子项显示。

```text
- Samsung SSD 990 Pro（SSD，内部驱动器，设备: 1）
  - C: （系统）
```

主要列：

| 列 | 说明 |
|---|---|
| 选择 | 选择要导出到思维导图的分区。物理磁盘本体不能选择。 |
| 顺序 | 以 `1 - 1:1` 显示全局顺序和设备内顺序。 |
| 驱动器（卷标） | 例如 `C: （系统）`。 |
| 分组 | 用户自定义分类，可编辑。 |
| 用途 | 例如系统、工作、备份，可编辑。 |
| 类型 | 内部 SSD、外部 HDD 等。 |
| 备注 | 用户备注，可编辑。 |
| 文件系统 | NTFS、exFAT 等。 |
| 使用情况 | 已用容量、使用率、剩余容量、总容量。 |
| 属性 | RO、H、OEM、NL、VSS 等。 |

主列表中只有 **分组**、**用途**、**备注** 可以编辑。

点击“顺序、驱动器、分组、类型、使用情况”的列名可以排序。默认按盘符 A-Z 排列。

## 更新磁盘信息

默认每 3 分钟自动刷新一次磁盘列表。需要立即更新时，点击 **刷新**。读取磁盘信息时会显示加载动画。

## 磁盘信息

点击 **磁盘信息** 可以打开磁盘信息窗口，查看总计、内部磁盘、外部磁盘等信息，包括磁盘名、设备顺序、内部/外部分类、接口、分区数量、使用情况、UUID 和 S.M.A.R.T 信息。信息可以保存为 TXT 报告。

## 生成思维导图

1. 勾选要导出的分区。
2. 点击 **生成树**。
3. 确认最大文件夹层级和同一文件夹内最大文件数量。
4. 选择保存位置。
5. 生成 DesktopNaotu 兼容的 `.km` 文件。

默认限制：

| 项目 | 默认值 |
|---|---:|
| 最大文件夹层级 | 48 |
| 同一文件夹内最大文件数 | 16 |

子文件夹不计入文件数量限制。

## 打开思维导图

点击 **查看树** 可以用 DesktopNaotu 打开最后生成的 `.km` 文件。第一次使用时需要选择 DesktopNaotu 的可执行文件。长按按钮可以选择其他 `.km` 文件。

## 分区右键菜单

右键点击分区行，可以打开分区、仅为该分区生成树、修改分组、查看分区信息、编辑用途和编辑备注。

## 分区信息与文件分析

分区信息窗口显示所选分区的设备、容量、属性和圆形使用率。点击 **文件分析** 后，会将文件分类为文档、音乐、视频、程序和其他。

分析后，右侧分类卡片显示容量和文件数量。`其他` 固定在最下方，其余分类按容量从大到小排列。点击 **文件列表** 或双击卡片，可以打开该分类的文件列表。文件列表每页 100 项，并支持按大小排序。

## 设置

点击 **设置** 可以调整 DriveMind。

| 标签页 | 内容 |
|---|---|
| 基本设置 | 自动刷新间隔、语言、主题、特殊分区、RAMDisk/WebDisk/远程驱动器显示、管理员启动、配置文件路径。 |
| DesktopNaotu | DesktopNaotu 可执行文件路径。 |
| 思维导图 | 输出规则、层级限制、文件数量限制。 |
| 分组 | 分组名、颜色和关联分区。 |
| 用途管理 | 每个分区的用途。 |
| 备注管理 | 每个分区的备注。 |
| 其他 | 更新检查、版本提示重置、全部设置初始化。 |

## 语言与主题

主窗口右上角有主题按钮和语言列表。

- 主题：`darkmode` / `lightmode`
- 语言：日语、英语、中文、韩语

也可以在 **设置 > 基本设置** 中修改。默认是日语和 darkmode。

## 更新检查

DriveMind 可以检查 GitHub Releases，并在有新版本时提示。DriveMind 只会打开 Release 页面，不会自动下载或自动安装。

## DesktopNaotu

DriveMind 生成 `.km` 文件，但不包含 DesktopNaotu 本体。请另外准备 DesktopNaotu。

DesktopNaotu：<https://github.com/naotu/desktopnaotu>

## 许可证

DriveMind 使用 **CC BY-NC-ND 4.0** 发布。需要署名，允许非商业分享，不允许分发修改版本。请查看 `LICENSE`、`LICENSE.ja`、`LICENSE.zh`、`LICENSE.kr`。

## 更新历史

请查看 `CHANGELOG.md`。

## 截图

### 磁盘信息

![磁盘信息](docs/screenshots/2_DiskInfo.png)

### 分区信息

![分区信息](docs/screenshots/3_PartitionInfo.png)

### 文件列表

![文件列表](docs/screenshots/4_FileList.png)

### 分组设置

![分组设置](docs/screenshots/5_Settings_Group.png)

## 作者

[@S2OUnicus](https://github.com/S2OUnicus)
