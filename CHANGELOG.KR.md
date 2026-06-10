# 변경 이력

[日本語](CHANGELOG.md) / [English](CHANGELOG.EN.md) / [中文](CHANGELOG.ZH.md) / [한국어](CHANGELOG.KR.md)

## v3.1.0

### 추가

- 파일 목록에 오른쪽 클릭 메뉴 추가
  - 파일 열기
  - 파일이 있는 폴더 열기
  - 파일 삭제(2회 확인)
  - 시스템 파일 속성 표시
- 파일 분석에 `이미지` 및 `아카이브` 분류 추가
- 파일 시스템 열에 BitLocker 상태 아이콘과 NTFS 버전 표시 추가

### 변경

- `음악` 분류를 `오디오`로 변경
- PyInstaller `--noconsole` 빌드 실행 시 보조 콘솔 창이 나타나기 어렵도록 조정
- 버전 번호를 `v3.1.0`으로 업데이트

## v3.0.0

### 추가

- 시작 시 `Brand.png`를 페이드인 / 페이드아웃으로 표시하는 스플래시 화면 추가
- README 상단에 `Brand.png` 추가
- 최신 업로드 이미지를 README 스크린샷에 반영
- `Brand.png`를 애플리케이션 리소스로 포함

### 변경

- 최신 기능에 맞게 README를 전면 정리
- 일본어, 영어, 중국어, 한국어 README 업데이트
- 일본어, 영어, 중국어, 한국어 CHANGELOG 업데이트
- PyInstaller 예시 명령에 `--add-data`를 추가하여 이미지 리소스를 쉽게 포함하도록 변경
- 버전 번호를 `v3.0.0`으로 업데이트

### 확인

- Python 구문 검사 완료
- ZIP 무결성 검사 완료

## v2.3.0

- lightmode 스타일 문제 수정
- DesktopNaotu로 `.km` 파일을 여는 처리 수정

## v2.2.0

- 트리 열기 흐름 개선
- 폴더 트리 생성 기능 추가
- 디스크 정보 표시 시 로딩 표시 추가
- 로그 크기 표시 추가

## v2.1.0

- 로그 기능 추가
- Doughnut Chart 표시 추가
- 마인드맵 출력 설정 확장

## v2.0.0

- GUI 다국어 전환 추가
- darkmode / lightmode 전환 추가
- README / CHANGELOG / LICENSE 관련 파일 다국어화

## v1.x

- 디스크 목록, `.km` 출력, DesktopNaotu 연동, 설정 관리, 파일 분석 등의 기본 기능 구현
