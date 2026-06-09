# DriveMind

[日本語](README.md) / [English](README.EN.md) / [中文](README.ZH.md) / [한국어](README.KR.md)

**DriveMind** is a Windows utility for viewing disk information, checking capacity usage, and generating folder-structure mind maps. It can list internal disks, external disks, partitions, drive letters, and volume labels, then export selected drives as DesktopNaotu-compatible `.km` files.

> Version: `v2.0.0`  
> Author: [@S2OUnicus](https://github.com/S2OUnicus)  
> Project: <https://github.com/S2OUnicus/DriveMind>  
> License: CC BY-NC-ND 4.0

![DriveMind main window](docs/screenshots/1_Index.png)

## What DriveMind can do

- Show connected disks, partitions, drive letters, labels, file systems, and attributes.
- Display internal and external disk totals separately.
- Show used space, usage percentage, free space, and total capacity with progress bars.
- Assign a group, purpose, and memo to each partition.
- Set colors for groups and show the color in the group column.
- Export selected drives as DesktopNaotu `.km` mind maps.
- Open generated `.km` files with DesktopNaotu.
- Open a partition information panel with usage and file-type analysis.
- Open categorized file lists with paging and size sorting.
- Hide or show RAM disks, WebDisks, network drives, and special partitions.
- Switch the GUI language between Japanese, English, Chinese, and Korean.
- Switch between darkmode and lightmode.
- Check GitHub Releases for new versions.

## Running the development version

Prepare Python 3.10 or later, then run the following commands in the repository folder.

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m drivemind
```

On Windows, you can also use:

```text
scripts/run_dev.bat
scripts/run_dev.ps1
```

Example PyInstaller command:

```powershell
pyinstaller --onefile --noconsole --name DriveMind --icon=src\drivemind\assets\logo.ico --paths src src\drivemind\__main__.py
```

The executable is usually created at `dist\DriveMind.exe`.

## Main window

The upper area shows a tree list of disks and partitions. The lower area shows capacity totals and action buttons. Physical disks are parent rows; partitions are child rows.

```text
- Samsung SSD 990 Pro (SSD, internal drive, device: 1)
  - C: (System)
```

Main columns:

| Column | Description |
|---|---|
| Select | Select partitions for mind map export. Physical disk rows cannot be selected. |
| Order | Shows global order and per-device order, such as `1 - 1:1`. |
| Drive (Label) | Shows the drive letter and volume label, such as `C: (System)`. |
| Group | User-defined group. Editable. |
| Purpose | User-defined purpose. Editable. |
| Type | Internal SSD, external HDD, and so on. |
| Memo | User memo. Editable. |
| File system | NTFS, exFAT, and so on. |
| Usage | Used space, percentage, free space, and total capacity. |
| Attributes | RO, H, OEM, NL, VSS, and other attributes. |

Only **Group**, **Purpose**, and **Memo** are editable in the main list.

You can click these column headers to sort the list: Order, Drive, Group, Type, and Usage. The default order is drive letter A-Z.

## Refreshing disk information

The disk list is refreshed automatically every 3 minutes by default. Press **Refresh** to update immediately. A loading indicator is shown while disk information is being collected.

## Disk information

Press **Disk Information** to open the disk information window. It summarizes all disks, internal disks, and external disks. You can view disk names, device order, internal/external classification, interface, partition count, usage, UUID, and S.M.A.R.T. information. The information can be saved as a TXT report.

## Generating a mind map

1. Select the partitions you want to export.
2. Press **Generate Tree**.
3. Confirm the maximum folder depth and maximum number of files per folder.
4. Select an output path.
5. A DesktopNaotu-compatible `.km` file is generated.

Default export limits:

| Option | Default |
|---|---:|
| Maximum folder depth | 48 |
| Maximum files in the same folder | 16 |

Subfolders are not counted as files.

Basic output structure:

```text
- Attribute: Device name
  - Drive letter: Label
    - Folder
      - Subfolder
```

## Opening a mind map

Press **Open Tree** to open the last generated `.km` file with DesktopNaotu. On first use, select the DesktopNaotu executable. Long-press the button to choose another `.km` file.

## Partition context menu

Right-click a partition row to open it, generate a mind map for that partition, change its group, open partition information, edit purpose, or edit memo.

## Partition information and file analysis

The partition information window shows the selected partition, its device, capacity, attributes, and circular usage display. Press **File Analysis** to categorize files into:

- Documents
- Music
- Videos
- Programs
- Other

After analysis, category cards show size and file count. **Other** is always placed at the bottom; the remaining categories are sorted by size. Press **File List** or double-click a card to open the categorized file list. The file list shows 100 items per page and can sort by file size.

## Settings

Open **Settings** to change DriveMind behavior.

| Tab | Description |
|---|---|
| Basic | Refresh interval, language, theme, special partitions, RAMDisk/WebDisk/remote-drive display, admin launch, config file path. |
| DesktopNaotu | DesktopNaotu executable path. |
| Mindmap | Folder/file output rules, depth limit, file count limit. |
| Group | Group names, colors, and related partitions. |
| Purpose | Purpose text per partition. |
| Memo | Memo text per partition. |
| Other | Update checks, reset version notices, reset all settings. |

## Language and theme

The top-right area of the main window contains a theme button and a language list.

- Theme: `darkmode` / `lightmode`
- Languages: Japanese, English, Chinese, Korean

The same options are also available in **Settings > Basic**. The default is Japanese and darkmode.

## Update check

DriveMind can check GitHub Releases and notify you when a new version is available. The interval can be changed in **Settings > Other**. DriveMind only opens the Release page; it does not automatically download or install updates.

## DesktopNaotu

DriveMind generates `.km` files but does not include DesktopNaotu. Prepare DesktopNaotu separately to open the generated mind maps.

DesktopNaotu: <https://github.com/naotu/desktopnaotu>

## License

DriveMind is released under **CC BY-NC-ND 4.0**. Attribution is required, non-commercial sharing is allowed, and distributing modified versions is not allowed. See `LICENSE`, `LICENSE.ja`, `LICENSE.zh`, and `LICENSE.kr`.

## Changelog

See `CHANGELOG.md` for changes.

## Screenshots

### Disk information

![Disk information](docs/screenshots/2_DiskInfo.png)

### Partition information

![Partition information](docs/screenshots/3_PartitionInfo.png)

### File list

![File list](docs/screenshots/4_FileList.png)

### Group settings

![Group settings](docs/screenshots/5_Settings_Group.png)

## Author

[@S2OUnicus](https://github.com/S2OUnicus)
