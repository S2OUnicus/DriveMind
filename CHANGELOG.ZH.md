# 更新日志

[日本語](CHANGELOG.md) / [English](CHANGELOG.EN.md) / [中文](CHANGELOG.ZH.md) / [한국어](CHANGELOG.KR.md)

## v3.1.0

### 新增

- 在文件列表中新增右键菜单
  - 打开文件
  - 打开文件所在文件夹
  - 删除文件（二次确认）
  - 显示系统文件属性
- 文件分析新增「图片」和「压缩包 / 归档」分类
- 文件系统列新增 BitLocker 状态图标和 NTFS 版本显示

### 变更

- 将「音乐」分类改名为「音频」
- 减少 PyInstaller `--noconsole` 打包后启动时出现的辅助控制台窗口
- 将版本号更新为 `v3.1.0`

## v3.0.0

### 新增

- 启动时以淡入 / 淡出的方式显示 `Brand.png`
- 在 README 顶部加入 `Brand.png`
- 使用最新上传的图片更新 README 截图
- 将 `Brand.png` 作为程序资源一并打包

### 变更

- 根据最新功能重新整理 README
- 更新日语、英语、中文、韩语 README
- 更新日语、英语、中文、韩语 CHANGELOG
- 在 PyInstaller 示例命令中加入 `--add-data`，方便打包图片资源
- 将版本号更新为 `v3.0.0`

### 检查

- 已进行 Python 语法检查
- 已进行 ZIP 完整性检查

## v2.3.0

- 修复 lightmode 配色问题
- 修复使用 DesktopNaotu 打开 `.km` 文件的处理

## v2.2.0

- 改进“打开树”流程
- 新增“文件夹树生成”功能
- 为磁盘信息窗口添加加载显示
- 新增日志大小显示

## v2.1.0

- 新增日志功能
- 新增 Doughnut Chart 显示
- 扩展思维导图输出设置

## v2.0.0

- 新增 GUI 多语言切换
- 新增 darkmode / lightmode 切换
- 新增多语言 README / CHANGELOG / LICENSE 相关文件

## v1.x

- 实现磁盘列表、`.km` 输出、DesktopNaotu 联动、设置管理、文件分析等基础功能
