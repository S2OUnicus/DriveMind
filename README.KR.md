# DriveMind

[日本語](README.md) / [English](README.EN.md) / [中文](README.ZH.md) / [한국어](README.KR.md)

![DriveMind Brand](docs/screenshots/Brand.png)

DriveMind는 Windows의 디스크 및 파티션 정보를 확인하고, 선택한 드라이브나 임의의 폴더 구조를 DesktopNaotu용 `.km` 마인드맵 파일로 내보내는 데스크톱 애플리케이션입니다.

저장 공간 확인, 외장 SSD 정리, 자료 드라이브 관리, 프로젝트 폴더 구조 시각화 등에 사용할 수 있습니다.

![메인 화면](docs/screenshots/1_Index.png)

## 주요 기능

- 내부 디스크, 외부 디스크, 파티션을 트리 형태로 확인
- 사용량, 남은 용량, 사용률을 Progress Bar로 표시
- 각 파티션에 그룹, 용도, 메모를 기록
- 그룹 색상을 설정하고 메인 목록의 그룹 열에 표시
- 선택한 파티션에서 DesktopNaotu `.km` 마인드맵 생성
- 임의의 폴더를 기준으로 `.km` 마인드맵 생성
- 최근 생성한 맵 또는 임의의 `.km` 파일을 DesktopNaotu로 열기
- 디스크 정보, 파티션 정보, 파일 분류 분석 표시
- 파일 분석 결과에서 분류별 파일 목록 열기
- 일본어, 영어, 중국어, 한국어 GUI 전환
- darkmode / lightmode 전환
- GitHub Releases에서 새 버전 확인
- 시작 시 Brand 이미지를 페이드인 / 페이드아웃으로 표시

## 실행 방법

프로젝트 폴더에서 다음 명령을 실행합니다.

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m drivemind
```

Windows exe 빌드 예시는 다음과 같습니다.

```powershell
pyinstaller --onefile --noconsole --name DriveMind --icon=src\drivemind\assets\logo_pure.ico --add-data "src\drivemind\assets;drivemind\assets" --paths src src\drivemind\__main__.py
```

생성된 실행 파일은 보통 `dist\DriveMind.exe`에 저장됩니다.

## 기본 사용 방법

### 1. 디스크 목록 확인

DriveMind를 실행하면 메인 화면에 감지된 디스크와 파티션이 표시됩니다.

각 파티션에는 드라이브 문자, 라벨, 종류, 파일 시스템, 사용 상태, 속성 등이 표시됩니다.

디스크 장치 행은 선택할 수 없습니다. `.km` 출력 대상으로 선택할 수 있는 것은 드라이브 문자가 있는 파티션입니다.

### 2. 그룹, 용도, 메모 편집

메인 화면에서는 다음 열만 편집할 수 있습니다.

- 그룹
- 용도
- 메모

그룹은 우클릭 메뉴나 설정 창에서 관리할 수 있습니다. 그룹 색상을 설정하면 메인 목록의 그룹 열에만 배경색으로 표시됩니다.

### 3. 선택한 드라이브에서 마인드맵 생성

1. 왼쪽 체크박스로 대상 파티션을 선택합니다
2. `選択した木生成` 버튼을 클릭합니다
3. 폴더 최대 깊이와 같은 폴더 내 최대 파일 수를 확인합니다
4. 저장 위치를 선택합니다
5. DesktopNaotu용 `.km` 파일이 생성됩니다

기본 폴더 최대 깊이는 48단계이며, 같은 폴더 안의 최대 파일 수는 16개입니다. 하위 폴더는 파일 수에 포함하지 않습니다.

### 4. 임의 폴더에서 마인드맵 생성

`フォルダ木生成` 버튼을 클릭하고 폴더를 선택합니다.

DriveMind는 선택한 폴더를 루트로 하여 내부 폴더와 파일 구조만 `.km`으로 출력합니다.

### 5. 생성한 맵 열기

`木閲覧`을 클릭하면 다음 중 하나를 선택할 수 있습니다.

- 최근 맵
- 임의 맵

`최근 맵`은 마지막으로 생성한 `.km` 파일이 아직 존재할 때만 사용할 수 있습니다.

DesktopNaotu 경로가 설정되어 있지 않으면 먼저 `DesktopNaotu.exe`를 선택해야 합니다.

DriveMind는 다음 형식으로 DesktopNaotu를 실행합니다.

```powershell
DesktopNaotu.exe DriveMind.km
```

## 디스크 정보

`ディスク情報`를 클릭하면 전체 디스크, 내부 디스크, 외부 디스크의 요약 정보를 확인할 수 있습니다.

용량, 사용 공간, 남은 공간, 파티션 수, 인터페이스 정보를 확인할 수 있습니다.

## 파티션 정보

파티션을 우클릭하고 `パーティション情報`를 선택하면 해당 파티션의 상세 정보를 볼 수 있습니다.

사용률은 Doughnut Chart로 표시됩니다. 파일 분석을 실행하면 파일을 다음과 같이 분류합니다.

- 문서
- 음악
- 비디오
- 프로그램
- 기타

분류 항목의 `ファイルリスト` 버튼을 누르면 해당 분류의 파일 목록을 열 수 있습니다.

## 설정

`設定`에서 각종 설정을 변경할 수 있습니다.

### 기본 설정

- 자동 새로고침 간격
- 언어
- 테마
- 관리자 권한으로 실행 여부
- RAMDisk / WebDisk / 네트워크 드라이브 표시 여부
- ESP / MSR / OEM / 읽기 전용 / 숨김 파티션 표시 여부

### DesktopNaotu

- `DesktopNaotu.exe` 경로

### 마인드맵

- 폴더 최대 깊이
- 같은 폴더 내 최대 파일 수
- 장치 이름 출력 여부
- 숨김 파일 및 시스템 파일 처리
- 확장자 출력 여부
- 출력하지 않을 이름과 확장자
- 프로그램 폴더 내부도 출력할지 여부
- Adobe 프로젝트를 폴더만 출력할지 여부

### 그룹

- 그룹 추가 및 삭제
- 그룹 색상 설정
- 선택한 그룹에 속한 파티션 목록 확인

### 용도 및 메모 관리

용도와 메모는 파티션별 일대일 설정으로 관리됩니다. 중복된 내용도 허용됩니다.

### 로그

- 로그 레벨
- 보관 일수
- 크기 제한
- 현재 로그 크기
- 로그 열기
- 전체 로그 삭제

### 기타

- 업데이트 확인 주기
- 버전 알림 초기화
- 모든 설정 초기화

## 마인드맵 출력 참고

기본적으로 DriveMind는 다음과 같은 임시 파일이나 관리 파일을 출력에서 제외합니다.

- `node_modules`
- `__pycache__`
- `_`로 시작하는 일부 폴더
- IDE 설정 폴더
- `.log` 파일
- `.tmp` 파일
- Office 임시 파일
- `.DS_Store`
- `Thumbs.db`
- `desktop.ini`
- `autorun.inf`

필요하면 `설정 > 마인드맵`에서 변경할 수 있습니다.

## 스크린샷

### 메인 화면 / darkmode

![메인 화면](docs/screenshots/1_Index.png)

### 메인 화면 / lightmode

![메인 화면 lightmode](docs/screenshots/1_Index_LightMode.png)

### 디스크 정보

![디스크 정보](docs/screenshots/2_DiskInfo.png)

### 파티션 정보

![파티션 정보](docs/screenshots/3_PartitionInfo.png)

### 기본 설정

![기본 설정](docs/screenshots/5_Settings_General.png)

### 마인드맵 설정

![마인드맵 설정](docs/screenshots/5_Settings_Mindmap.png)

### 그룹 설정

![그룹 설정](docs/screenshots/5_Settings_Group.png)

## 작성자

- 작성자: [@S2OUnicus](https://github.com/S2OUnicus)
- 프로젝트: <https://github.com/S2OUnicus/DriveMind>

## 라이선스

이 프로젝트는 `CC-BY-NC-ND-4.0`으로 공개됩니다.

상업적 이용과 수정 버전의 재배포는 허용되지 않습니다. 자세한 내용은 `LICENSE`를 확인하세요.
