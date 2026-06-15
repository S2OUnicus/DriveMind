# Changelog

[日本語](CHANGELOG.md) / [English](CHANGELOG.EN.md) / [中文](CHANGELOG.ZH.md) / [한국어](CHANGELOG.KR.md)

## v3.2.0

### Fixed

- Fixed an issue where the disk list could appear empty when DriveMind was started without administrator privileges.
- Improved fallback behavior so DriveMind can continue scanning with psutil when PowerShell-based disk detection fails or times out.
- Added a secondary `psutil.disk_partitions(all=True)` scan when `all=False` returns no partitions.
- Fixed an issue where normal non-BitLocker partitions could be displayed with the `🔓` icon.
- Improved BitLocker detection by combining ProtectionStatus, VolumeStatus, LockStatus, and EncryptionPercentage.
- Updated the version number to `v3.2.0`.

## v3.1.0

### Added

- Added a right-click menu to the file list
  - Open file
  - Open containing folder
  - Delete file with two confirmations
  - Show system file properties
- Added `Image` and `Archive` categories to file analysis
- Added BitLocker status icons and NTFS version display to the file system column

### Changed

- Renamed the `Music` category to `Audio`
- Reduced unwanted helper console windows when running a PyInstaller `--noconsole` build
- Updated the version number to `v3.1.0`

## v3.0.0

### Added

- Added a startup splash screen that shows `Brand.png` with fade-in and fade-out animation
- Added `Brand.png` near the top of the README files
- Updated README screenshots with the latest uploaded images
- Bundled `Brand.png` as an application asset

### Changed

- Rewrote the README files to match the latest features
- Updated Japanese, English, Chinese, and Korean README files
- Updated Japanese, English, Chinese, and Korean CHANGELOG files
- Added `--add-data` to the PyInstaller example command so image assets can be bundled more easily
- Updated the version number to `v3.0.0`

### Verified

- Ran Python syntax checks
- Verified ZIP archive integrity

## v2.3.0

- Fixed lightmode styling
- Fixed opening `.km` files with DesktopNaotu

## v2.2.0

- Improved the Open Tree workflow
- Added Generate Folder Tree
- Added loading display for disk information
- Added log size display

## v2.1.0

- Added logging features
- Added Doughnut Chart display
- Expanded mind map output settings

## v2.0.0

- Added multilingual GUI switching
- Added darkmode / lightmode switching
- Added multilingual README / CHANGELOG / LICENSE-related files

## v1.x

- Implemented the main disk list, `.km` export, DesktopNaotu integration, settings, and file analysis features
