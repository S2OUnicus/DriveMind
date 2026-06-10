# DriveMind

[日本語](README.md) / [English](README.EN.md) / [中文](README.ZH.md) / [한국어](README.KR.md)

![DriveMind Brand](docs/screenshots/Brand.png)

DriveMind is a Windows desktop application for checking disk and partition information and exporting selected drives or folders as DesktopNaotu `.km` mind maps.

It is useful for storage review, external SSD organization, archive management, project folder visualization, and disk usage checking.

![Main window](docs/screenshots/1_Index.png)

## What DriveMind can do

- Show internal disks, external disks, and partitions in a tree-style list
- Display used space, free space, and usage percentage with progress bars
- Save group, purpose, and memo information for each partition
- Assign colors to groups and show them in the main list
- Generate DesktopNaotu `.km` mind maps from selected partitions
- Generate `.km` mind maps from any selected folder
- Open the latest generated map or any `.km` file with DesktopNaotu
- Show disk information, partition information, and file category analysis
- Open file lists from file analysis categories
- Switch GUI language between Japanese, English, Chinese, and Korean
- Switch between darkmode and lightmode
- Check new versions from GitHub Releases
- Show the Brand image with a fade-in / fade-out splash screen on startup

## How to run

Run the following commands in the project folder.

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m drivemind
```

Example command for building a Windows executable:

```powershell
pyinstaller --onefile --noconsole --name DriveMind --icon=src\drivemind\assets\logo_pure.ico --add-data "src\drivemind\assets;drivemind\assets" --paths src src\drivemind\__main__.py
```

The generated executable will normally be placed in `dist\DriveMind.exe`.

## Basic usage

### 1. Check the disk list

When DriveMind starts, the main window shows detected disks and partitions.

Each partition can show drive letter, label, type, file system, usage status, and attributes.

Disk device rows cannot be selected. Only partitions with drive letters can be selected as mind map output targets.

### 2. Edit group, purpose, and memo

Only the following columns are editable in the main window:

- Group
- Purpose
- Memo

Groups can be managed from the context menu or the settings window. When a group color is set, it appears only in the group column of the main list.

### 3. Generate a mind map from selected drives

1. Select target partitions with checkboxes
2. Click `Generate selected tree`
3. Check the folder depth and file count options
4. Choose an output path
5. A DesktopNaotu `.km` file will be generated

The default maximum folder depth is 48 levels, and the default maximum file count in one folder is 16. Subfolders are not counted as files.

### 4. Generate a mind map from any folder

Click `Generate folder tree` and select a folder.

DriveMind will use the selected folder as the root and export only the folder and file structure inside it.

### 5. Open a generated map

Click `Open tree` and choose one of the following options:

- Recent map
- Any map

`Recent map` is enabled only when the last generated `.km` file still exists.

If the DesktopNaotu path is not configured, select `DesktopNaotu.exe` first.

DriveMind launches DesktopNaotu in this format:

```powershell
DesktopNaotu.exe DriveMind.km
```

## Disk information

Click `Disk information` to view summary information for all disks, internal disks, and external disks.

You can check capacity, used space, free space, partition count, and interface information.

## Partition information

Right-click a partition and choose `Partition information` to view details for that partition.

Usage is shown as a Doughnut Chart. File analysis can classify files into categories such as:

- Documents
- Music
- Video
- Programs
- Others

Click the `File list` button for a category to open a list of files in that category.

## Settings

Open `Settings` to configure DriveMind.

### General

- Auto refresh interval
- Language
- Theme
- Run as administrator
- Show or hide RAMDisk / WebDisk / network drives
- Show or hide ESP / MSR / OEM / read-only / hidden partitions

### DesktopNaotu

- Path to `DesktopNaotu.exe`

### Mind map

- Maximum folder depth
- Maximum file count in one folder
- Output device name or not
- Hidden/system file options
- Extension output option
- Excluded names and extensions
- Program folder output option
- Adobe project folder-only output option

### Groups

- Add and delete groups
- Set group colors
- View partitions that belong to the selected group

### Purpose and memo management

Purpose and memo are managed as one-to-one settings for each partition. Duplicate text is allowed.

### Log

- Log level
- Retention days
- Size limit
- Current log size
- Open logs
- Delete all logs

### Other

- Update check frequency
- Reset hidden update notifications
- Reset all settings

## Mind map output notes

By default, DriveMind excludes temporary and management files such as:

- `node_modules`
- `__pycache__`
- folders starting with `_`
- IDE setting folders
- `.log` files
- `.tmp` files
- Office temporary files
- `.DS_Store`
- `Thumbs.db`
- `desktop.ini`
- `autorun.inf`

You can change these options from `Settings > Mind map`.

## Screenshots

### Main window / darkmode

![Main window](docs/screenshots/1_Index.png)

### Main window / lightmode

![Main window lightmode](docs/screenshots/1_Index_LightMode.png)

### Disk information

![Disk information](docs/screenshots/2_DiskInfo.png)

### Partition information

![Partition information](docs/screenshots/3_PartitionInfo.png)

### General settings

![General settings](docs/screenshots/5_Settings_General.png)

### Mind map settings

![Mind map settings](docs/screenshots/5_Settings_Mindmap.png)

### Group settings

![Group settings](docs/screenshots/5_Settings_Group.png)

## Author

- Author: [@S2OUnicus](https://github.com/S2OUnicus)
- Project: <https://github.com/S2OUnicus/DriveMind>

## License

This project is released under `CC-BY-NC-ND-4.0`.

Commercial use and redistribution of modified versions are not permitted. See `LICENSE` for details.
