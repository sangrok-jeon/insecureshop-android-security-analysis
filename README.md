# InsecureShop Android 보안 분석

## 1. 프로젝트 개요

`InsecureShop`은 로그인 로직, WebView, Android 컴포넌트, Content Provider, 네트워크 처리 등 다양한 모바일 보안 취약점을 포함한 실습용 Android 애플리케이션이다. 이 저장소는 `InsecureShop`의 취약점을 공식 문제 번호 기준으로 분석하고, 코드 근거와 동적 검증 결과를 함께 정리한 포트폴리오 프로젝트다.

## 2. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 정적 분석 | `jadx` |
| 동적 분석 | `adb`, `nox_adb`, Android Studio |
| 보조 도구 | `Burp Suite`, `Frida` |

## 3. 분석 방법

- `AndroidManifest.xml`을 우선 확인해 exported 컴포넌트, deeplink 진입점, provider 설정을 식별했다.
- `jadx`로 각 Activity, Provider, Utility 클래스의 입력 처리와 검증 로직을 추적했다.
- `adb` 및 `nox_adb`를 이용해 deeplink 호출, component 접근, `content query`, `logcat` 확인을 수행했다.
- `adb`만으로 재현이 어려운 항목은 Android Studio 기반 PoC 앱을 사용해 일반 서드파티 앱 관점에서 검증했다.

## 4. 완료한 취약점 분석

### 4.1 Hardcoded Credentials

상세 보고서: [01-hardcoded-credentials.md](./findings/01-hardcoded-credentials.md)

로그인 로직을 분석한 결과, 계정 정보가 애플리케이션 내부 코드에 하드코딩되어 있었고 APK 디컴파일만으로 식별한 자격증명을 이용해 정상 로그인까지 가능함을 확인하였다.

### 4.2 Insufficient URL Validation

상세 보고서: [02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md)

`WebViewActivity`의 `/web` 경로에서는 deeplink로 전달된 `url` 파라미터가 충분한 검증 없이 바로 `loadUrl()`로 전달되었다. 그 결과 앱 내부 WebView에서 임의 외부 URL을 직접 로드할 수 있었다.

### 4.3 Weak Host Validation Check

상세 보고서: [02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md)

`/webview` 경로에서는 검증이 존재했지만, 실제 host 비교가 아니라 `endsWith("insecureshopapp.com")` 같은 약한 문자열 비교만 수행하고 있었다. 이를 이용해 실제 host가 허용 도메인이 아니더라도 검증 우회가 가능함을 확인하였다.

### 4.5 Access to Protected Components

상세 보고서: [05-access-to-protected-components.md](./findings/05-access-to-protected-components.md)

`WebView2Activity`는 외부에서 전달된 `extra_intent`를 검증 없이 `startActivity()`로 실행하고 있었고, PoC 앱 검증 결과 이를 통해 `PrivateActivity`와 같은 protected component가 우회 호출될 수 있음을 확인하였다.

### 4.15 Insecure Content Provider

상세 보고서: [15-insecure-content-provider.md](./findings/15-insecure-content-provider.md)

`InsecureShopProvider`는 `content://com.insecureshop.provider/insecure` URI에 대한 query 요청에서 `username`과 `password`를 그대로 반환하고 있었다. 실제로 `nox_adb shell content query` 명령만으로 자격증명이 직접 조회되었다.

## 5. 결론

현재 저장소에는 공식 문제 번호 기준으로 `1`, `2`, `3`, `5`, `15`번 항목이 정리되어 있다. 이 중 `2`와 `3`은 동일한 `WebViewActivity`의 deeplink 처리 구조에서 함께 확인되어 하나의 상세 보고서로 통합해 정리하였다. 이후 문서도 동일한 번호 체계를 유지하면서 순차적으로 확장할 예정이며, 각 보고서는 정적 분석 근거와 동적 검증 결과를 함께 제시하는 형식으로 이어간다.
