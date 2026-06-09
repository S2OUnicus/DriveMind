# DriveMind

[日本語](README.md) / [English](README.EN.md) / [中文](README.ZH.md) / [한국어](README.KR.md)

**DriveMind**는 Windows용 디스크 정보 표시, 용량 확인, 폴더 구조 마인드맵 생성 도구입니다. 내부 디스크, 외부 디스크, 파티션, 드라이브 문자, 볼륨 라벨을 표시하고 선택한 드라이브를 DesktopNaotu 호환 `.km` 파일로 내보낼 수 있습니다.

> 버전: `v2.0.0`  
> 작성자: [@S2OUnicus](https://github.com/S2OUnicus)  
> 프로젝트: <https://github.com/S2OUnicus/DriveMind>  
> 라이선스: CC BY-NC-ND 4.0

![DriveMind main window](docs/screenshots/1_Index.png)

## 할 수 있는 일

- 연결된 디스크, 파티션, 드라이브 문자, 라벨, 파일 시스템, 속성을 표시합니다.
- 내부 디스크와 외부 디스크의 용량 합계를 따로 확인합니다.
- 진행 막대로 사용 용량, 사용률, 남은 용량, 전체 용량을 확인합니다.
- 파티션별로 그룹, 용도, 메모를 설정합니다.
- 그룹에 색상을 지정하고 메인 화면의 그룹 열에 표시합니다.
- 선택한 드라이브의 폴더 구조를 DesktopNaotu용 `.km` 마인드맵으로 내보냅니다.
- 생성한 `.km` 파일을 DesktopNaotu로 엽니다.
- 파티션 정보 화면에서 용량, 속성, 사용률, 파일 종류별 분석을 확인합니다.
- 분류별 파일 목록을 페이지 단위로 보고 크기순 정렬을 할 수 있습니다.
- RAM 디스크, WebDisk, 네트워크 드라이브, 특수 파티션의 표시 여부를 설정합니다.
- GUI 언어를 일본어, 영어, 중국어, 한국어로 전환합니다.
- darkmode / lightmode를 전환합니다.
- GitHub Releases에서 새 버전을 확인합니다.

## 개발 버전 실행

Python 3.10 이상을 준비하고 저장소 폴더에서 다음을 실행합니다.

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m drivemind
```

Windows에서는 다음 스크립트도 사용할 수 있습니다.

```text
scripts/run_dev.bat
scripts/run_dev.ps1
```

PyInstaller 빌드 예시:

```powershell
pyinstaller --onefile --noconsole --name DriveMind --icon=src\drivemind\assets\logo.ico --paths src src\drivemind\__main__.py
```

실행 파일은 보통 `dist\DriveMind.exe`에 생성됩니다.

## 메인 화면

상단에는 디스크와 파티션 목록이, 하단에는 용량 합계와 기능 버튼이 표시됩니다. 물리 디스크는 부모 행으로, 파티션은 자식 행으로 표시됩니다.

```text
- Samsung SSD 990 Pro (SSD, 내부 드라이브, 장치: 1)
  - C: (시스템)
```

주요 열:

| 열 | 설명 |
|---|---|
| 선택 | 마인드맵으로 내보낼 파티션을 선택합니다. 물리 디스크 행은 선택할 수 없습니다. |
| 순서 | 전체 순서와 장치 내 순서를 `1 - 1:1` 형식으로 표시합니다. |
| 드라이브(라벨) | 예: `C: (시스템)`. |
| 그룹 | 사용자 지정 그룹입니다. 편집할 수 있습니다. |
| 용도 | 예: 시스템, 작업, 백업. 편집할 수 있습니다. |
| 종류 | 내부 SSD, 외부 HDD 등. |
| 메모 | 사용자 메모입니다. 편집할 수 있습니다. |
| 파일 시스템 | NTFS, exFAT 등. |
| 사용 현황 | 사용 용량, 사용률, 남은 용량, 전체 용량. |
| 속성 | RO, H, OEM, NL, VSS 등. |

메인 목록에서는 **그룹**, **용도**, **메모**만 편집할 수 있습니다.

순서, 드라이브, 그룹, 종류, 사용 현황 열을 클릭하면 정렬할 수 있습니다. 기본 정렬은 드라이브 문자 A-Z입니다.

## 디스크 정보 새로 고침

디스크 목록은 기본적으로 3분마다 자동 갱신됩니다. 즉시 갱신하려면 **새로 고침** 버튼을 누릅니다. 정보를 읽는 동안 로딩 표시가 나타납니다.

## 디스크 정보

**디스크 정보** 버튼을 누르면 전체, 내부 디스크, 외부 디스크의 정보를 확인할 수 있습니다. 디스크 이름, 장치 순서, 내부/외부 분류, 인터페이스, 파티션 수, 사용 현황, UUID, S.M.A.R.T 정보를 볼 수 있으며 TXT 보고서로 저장할 수 있습니다.

## 마인드맵 생성

1. 내보낼 파티션을 선택합니다.
2. **트리 생성** 버튼을 누릅니다.
3. 최대 폴더 깊이와 같은 폴더 내 최대 파일 수를 확인합니다.
4. 저장 위치를 선택합니다.
5. DesktopNaotu 호환 `.km` 파일이 생성됩니다.

기본 제한:

| 항목 | 기본값 |
|---|---:|
| 최대 폴더 깊이 | 48 |
| 같은 폴더 내 최대 파일 수 | 16 |

하위 폴더는 파일 수 제한에 포함되지 않습니다.

## 마인드맵 열기

**트리 열기** 버튼을 누르면 마지막으로 생성한 `.km` 파일을 DesktopNaotu로 엽니다. 처음 사용할 때는 DesktopNaotu 실행 파일을 선택합니다. 다른 `.km` 파일을 열려면 버튼을 길게 누릅니다.

## 파티션 우클릭 메뉴

파티션 행을 우클릭하면 파티션 열기, 해당 파티션만 트리 생성, 그룹 변경, 파티션 정보, 용도 편집, 메모 편집을 사용할 수 있습니다.

## 파티션 정보와 파일 분석

파티션 정보 창에서는 선택한 파티션의 장치, 용량, 속성, 원형 사용률을 확인합니다. **파일 분석**을 누르면 파일을 문서, 음악, 비디오, 프로그램, 기타로 분류하여 용량을 집계합니다.

분석 후 오른쪽 카드에 용량과 파일 수가 표시됩니다. `기타`는 항상 맨 아래에 표시되고 나머지는 용량이 큰 순서로 정렬됩니다. **파일 목록** 버튼 또는 카드 더블 클릭으로 해당 분류의 파일 목록을 열 수 있습니다. 파일 목록은 100개 단위로 페이지가 나뉘며 크기순 정렬을 지원합니다.

## 설정

**설정** 버튼에서 DriveMind 동작을 변경할 수 있습니다.

| 탭 | 내용 |
|---|---|
| 기본 설정 | 자동 갱신 간격, 언어, 테마, 특수 파티션, RAMDisk/WebDisk/원격 드라이브 표시, 관리자 실행, 설정 파일 경로. |
| DesktopNaotu | DesktopNaotu 실행 파일 경로. |
| 마인드맵 | 출력 규칙, 깊이 제한, 파일 수 제한. |
| 그룹 | 그룹 이름, 색상, 관련 파티션. |
| 용도 관리 | 파티션별 용도. |
| 메모 관리 | 파티션별 메모. |
| 기타 | 업데이트 확인, 버전 알림 초기화, 전체 설정 초기화. |

## 언어와 테마

메인 창 오른쪽 위에 테마 버튼과 언어 목록이 있습니다.

- 테마: `darkmode` / `lightmode`
- 언어: 일본어, 영어, 중국어, 한국어

같은 설정은 **설정 > 기본 설정**에서도 변경할 수 있습니다. 기본값은 일본어와 darkmode입니다.

## 업데이트 확인

DriveMind는 GitHub Releases를 확인하고 새 버전이 있으면 알릴 수 있습니다. DriveMind는 Release 페이지를 열기만 하며 자동 다운로드나 자동 설치는 하지 않습니다.

## DesktopNaotu

DriveMind는 `.km` 파일을 생성하지만 DesktopNaotu 자체는 포함하지 않습니다. 마인드맵을 열려면 DesktopNaotu를 별도로 준비하세요.

DesktopNaotu: <https://github.com/naotu/desktopnaotu>

## 라이선스

DriveMind는 **CC BY-NC-ND 4.0**으로 공개됩니다. 저작자 표시가 필요하며, 비영리 공유는 가능하지만 수정본 배포는 허용되지 않습니다. `LICENSE`, `LICENSE.ja`, `LICENSE.zh`, `LICENSE.kr`를 확인하세요.

## 변경 내역

변경 사항은 `CHANGELOG.md`에 기록합니다.

## 스크린샷

### 디스크 정보

![Disk information](docs/screenshots/2_DiskInfo.png)

### 파티션 정보

![Partition information](docs/screenshots/3_PartitionInfo.png)

### 파일 목록

![File list](docs/screenshots/4_FileList.png)

### 그룹 설정

![Group settings](docs/screenshots/5_Settings_Group.png)

## 작성자

[@S2OUnicus](https://github.com/S2OUnicus)
