# InsecureShop - Weak Host Validation Check

## 1. 개요

`InsecureShop`의 `WebViewActivity`를 분석한 결과, `/webview` 경로에서는 URL 검증이 존재하지만 실제 host 비교가 아닌 문자열 suffix 비교만 수행하고 있음을 확인하였다. 이로 인해 실제 host가 허용 도메인이 아니어도, 문자열 끝부분만 맞추면 검증 우회가 가능했다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Weak Host Validation Check` |
| 취약점 유형 | Deeplink 기반 부정확한 host 검증 |
| 영향 | 허용 도메인처럼 보이는 값으로 WebView URL 검증 우회 가능 |
| 분석 도구 | `jadx`, `nox_adb`, `Nox` |
| 핵심 컴포넌트 | `WebViewActivity` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | Android |
| 정적 분석 | `jadx` |
| 동적 검증 | `nox_adb shell am start` |

## 4. 분석 방법

이번 항목은 `/webview` 경로의 검증 로직이 실제 host 기반인지 여부를 기준으로 분석하였다.

1. `AndroidManifest.xml`에서 `WebViewActivity`가 deeplink 진입점임을 확인하였다.
2. `WebViewActivity`의 `/webview` 분기에서 `url` 파라미터 검증 로직을 추적하였다.
3. `endsWith("insecureshopapp.com")` 기반 문자열 비교가 실제 host 비교를 대체하고 있음을 확인하였다.
4. 우회용 deeplink를 호출해 실제 host가 `naver.com`이어도 검증이 통과하는지 검증하였다.

## 5. 상세 분석

### 5.1 Deeplink 진입점 확인

`WebViewActivity`는 `VIEW` 및 `BROWSABLE` 인텐트 필터를 통해 외부 deeplink 입력을 직접 처리한다. 따라서 `/webview` 경로에 전달되는 `url` 파라미터의 검증 방식이 곧 WebView 보안에 직접 영향을 준다.

### 5.2 `/webview` 분기의 약한 검증 로직

`/webview` 분기에서는 `url` 파라미터를 추출한 뒤 아래와 같은 조건으로 검증한다.

```java
if (StringsKt.endsWith$default(queryParameter, "insecureshopapp.com", false, 2, null)) {
    data = ...
}
```

문제는 이 검증이 `Uri.parse(url).getHost()`처럼 실제 host를 파싱해서 비교하는 방식이 아니라, 전체 문자열이 `insecureshopapp.com`으로 끝나는지만 확인한다는 점이다.

즉 아래 값은:

```text
https://naver.com/?q=insecureshopapp.com
```

실제 host가 `naver.com`이지만, 문자열 끝이 `insecureshopapp.com`으로 끝나기 때문에 조건을 통과할 수 있다. 이후 값은 그대로 `webview.loadUrl(data)`로 전달되므로, 검증이 존재하더라도 우회 가능한 구조가 된다.

### 5.3 동적 검증

실제 우회는 아래 명령으로 확인하였다.

```powershell
nox_adb shell am start -W -a android.intent.action.VIEW -d "insecureshop://com.insecureshop/webview?url=https%3A%2F%2Fnaver.com%2F%3Fq%3Dinsecureshopapp.com" com.insecureshop
```

실행 결과 실제 host는 `naver.com`임에도 불구하고 앱 내부 WebView가 로드되었다. 이는 `/webview` 분기의 검증이 host 기반이 아니라 문자열 suffix 비교에 불과해 우회 가능함을 보여준다.

## 6. 영향도

개발자는 허용 도메인만 열도록 검증을 구현했다고 생각할 수 있지만, 실제로는 문자열 일부만 맞춰도 검증이 통과한다. 그 결과 공격자는 허용 도메인처럼 보이는 URL을 구성해 앱 내부 WebView에 임의 웹페이지를 로드할 수 있으며, 피싱 페이지 노출이나 WebView 기반 추가 공격으로 이어질 수 있다.

## 7. 대응 방안

- 허용 도메인 검증은 `Uri.parse(url).getHost()`를 이용한 실제 host 비교로 구현해야 한다.
- `contains`, `startsWith`, `endsWith`와 같은 단순 문자열 비교를 도메인 검증에 사용하지 않아야 한다.
- 허용 가능한 scheme, host, path를 명시적으로 제한하는 allowlist 기반 검증을 적용해야 한다.

## 8. 결론

이번 분석에서는 `WebViewActivity`의 `/webview` 분기에서 검증 로직이 존재하더라도 실제 host 비교가 아니라 `endsWith("insecureshopapp.com")` 기반 문자열 비교만 수행하고 있음을 확인하였다. 동적 검증 결과 실제 host가 `naver.com`인 URL도 우회에 성공하여 `Weak Host Validation Check` 취약점이 성립함을 확인하였다.

## 9. 취약점 테스트

### 1. Deeplink 진입점 확인

![1. Deeplink 진입점 확인](../images/03-weak-host-validation-check/01-manifest-webview-entrypoint.png)

`WebViewActivity`는 외부 URI 기반 deeplink 진입점으로 동작하며, `/webview` 경로에서 전달된 `url` 파라미터가 이후 검증 로직을 거쳐 WebView에 로드된다.

### 2. `/webview` 경로의 검증 코드 확인

![2. `/webview` 경로의 검증 코드 확인](../images/03-weak-host-validation-check/02-webview-path-validation-code.png)

`/webview` 분기에서는 `url` 파라미터를 추출한 뒤 `endsWith("insecureshopapp.com")` 조건으로만 검증하고 있다. 이 로직은 실제 host가 아닌 전체 문자열 suffix만 보기 때문에 안전한 host 검증으로 볼 수 없다.

### 3. 약한 host 검증 우회 확인

사용 명령:

```powershell
nox_adb shell am start -W -a android.intent.action.VIEW -d "insecureshop://com.insecureshop/webview?url=https%3A%2F%2Fnaver.com%2F%3Fq%3Dinsecureshopapp.com" com.insecureshop
```

![3. 약한 host 검증 우회 확인](../images/03-weak-host-validation-check/04-webview-bypass-load-naver.png)

실행 결과 실제 host는 `naver.com`이지만 URL 문자열 끝이 `insecureshopapp.com`으로 끝난다는 이유로 검증을 통과해 WebView가 로드되었다. 이를 통해 weak host validation 우회가 가능함을 검증하였다.
