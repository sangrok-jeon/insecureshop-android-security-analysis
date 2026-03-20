# InsecureShop - WebView Deeplink URL Validation Issues

## 1. 개요

`InsecureShop`의 `WebViewActivity`를 분석한 결과, deeplink로 전달된 외부 URL을 WebView에 로드하는 과정에서 두 가지 문제가 함께 존재함을 확인하였다.

- `/web` 경로에서는 `url` 파라미터를 충분한 검증 없이 `webview.loadUrl()`에 전달한다.
- `/webview` 경로에서는 검증을 수행하지만, URL의 실제 host를 비교하지 않고 문자열 suffix 비교만 수행하여 우회 가능성이 존재한다.

즉 동일한 Activity 내부에서 `Insufficient URL Validation`과 `Weak Host Validation Check`가 서로 다른 분기로 함께 나타난다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Insufficient URL Validation`, `Weak Host Validation Check` |
| 취약점 유형 | Deeplink 기반 WebView URL 처리 취약점 |
| 영향 | 임의 URL 로드 가능, 허술한 검증 우회 가능 |
| 분석 도구 | `jadx`, `adb`, `Nox` |
| 핵심 컴포넌트 | `WebViewActivity` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | Android |
| 정적 분석 | `jadx` |
| 동적 검증 | `nox_adb shell am start` |

## 4. 접근 방식

이번 항목은 Manifest에서 deeplink 진입점을 확인한 뒤, `WebViewActivity`의 URI 처리 흐름과 URL 검증 로직을 따라가는 방식으로 분석하였다.

1. `AndroidManifest.xml`에서 `VIEW`, `BROWSABLE`, `scheme`, `host` 조합을 확인하였다.
2. `WebViewActivity`가 deeplink URI를 직접 처리하는 진입점임을 식별하였다.
3. `intent.getData()`로 전달된 URI에서 `url` 파라미터를 추출하는 흐름을 확인하였다.
4. `/web`와 `/webview` 경로별 분기를 비교하며 검증 유무와 검증 방식을 분석하였다.
5. `nox_adb shell am start` 명령으로 실제 deeplink를 호출하여 동적 검증을 수행하였다.

## 5. 상세 분석

### 5.1 Deeplink 진입점 식별

`AndroidManifest.xml` 분석 결과, `WebViewActivity`는 `android.intent.action.VIEW`와 `android.intent.category.BROWSABLE`를 사용하는 `intent-filter`를 가지고 있으며, `insecureshop://com.insecureshop` 형태의 URI를 처리하도록 구성되어 있었다.

반면 `WebView2Activity`는 별도의 custom action만 선언하고 있을 뿐 `scheme`과 `host`가 정의되어 있지 않았다. 따라서 이번 이슈에서 외부 URI 기반 deeplink 진입점은 `WebViewActivity`로 판단하였다.

### 5.2 `/web` 경로의 Insufficient URL Validation

`WebViewActivity` 내부에서는 `intent.getData()`로 전달된 URI를 기준으로 경로를 분기한다. 이 중 `/web` 경로에서는 `url` 파라미터를 그대로 꺼내어 `data` 변수에 대입한 뒤, 별도의 allowlist 검증 없이 `webview.loadUrl(data)`를 호출한다.

즉 공격자는 아래와 같은 형태로 임의의 URL을 앱 내부 WebView에 로드할 수 있다.

```text
insecureshop://com.insecureshop/web?url=https://naver.com
```

이 구조는 외부 입력으로 전달된 URL이 충분히 검증되지 않은 채 곧바로 위험 동작인 `loadUrl()`에 도달한다는 점에서 `Insufficient URL Validation`에 해당한다.

### 5.3 `/webview` 경로의 Weak Host Validation Check

`/webview` 경로에서는 `url` 파라미터를 추출한 뒤 다음 조건으로 검증을 수행한다.

```java
if (StringsKt.endsWith$default(queryParameter, "insecureshopapp.com", false, 2, null)) {
    data = ...
}
```

문제는 이 검증이 URL의 실제 host를 파싱해 비교하는 방식이 아니라, 전체 문자열이 `insecureshopapp.com`으로 끝나는지만 확인한다는 점이다.

즉 아래와 같은 값은 실제 host가 `naver.com`이더라도 문자열 끝이 `insecureshopapp.com`이므로 조건을 통과할 수 있다.

```text
https://naver.com/?q=insecureshopapp.com
```

이후 조건을 통과한 값은 그대로 `webview.loadUrl(data)`에 전달되므로, 검증이 존재하더라도 우회 가능한 약한 검증 구조가 된다.

### 5.4 두 분기의 차이

두 취약점은 비슷해 보이지만 차이가 분명하다.

- `/web`는 검증이 사실상 존재하지 않는다.
- `/webview`는 검증은 존재하지만 구현이 부정확해 우회 가능성이 있다.

즉 하나는 `검증 부족`, 다른 하나는 `검증 우회 가능` 문제다.

## 6. 영향도

이 구조를 악용하면 공격자는 앱의 신뢰를 빌려 임의 웹페이지를 앱 내부 WebView에 띄울 수 있다. 그 결과 사용자는 정상 앱 화면으로 오인할 수 있으며, 피싱 페이지 노출, 임의 웹 콘텐츠 로딩, 추가 WebView 취약점과의 결합 위험이 발생할 수 있다.

특히 `/webview` 분기의 경우 개발자가 검증을 구현했다고 생각할 수 있지만, 실제로는 host 기반 검증이 아니라 문자열 suffix 비교만 수행하고 있어 보안적으로 잘못된 보호 장치가 된다.

## 7. 대응 방안

- deeplink로 전달된 외부 URL을 그대로 `loadUrl()`에 전달하지 않아야 한다.
- 허용 도메인 검증이 필요한 경우 `Uri.parse(url).getHost()`를 이용해 실제 host를 추출한 뒤 정확히 비교해야 한다.
- `contains`, `startsWith`, `endsWith`와 같은 단순 문자열 비교로 도메인 검증을 구현하지 않아야 한다.
- 허용 가능한 scheme, host, path를 명시적으로 제한하는 allowlist 기반 검증을 적용해야 한다.

## 8. 결론

이번 분석에서는 `WebViewActivity`를 통해 처리되는 deeplink URL 로직을 확인한 결과, `/web` 경로에서는 검증이 부족했고 `/webview` 경로에서는 검증이 존재하더라도 우회 가능한 수준에 머물러 있음을 확인하였다.

이를 통해 외부 입력을 WebView에 연결하는 구조에서는 단순히 검증 코드가 "존재하는지"보다, 그 검증이 실제 URL 구조를 기반으로 안전하게 구현되었는지가 더 중요하다는 점을 확인할 수 있었다.

## 9. 취약점 테스트

### 1. Deeplink 진입점 확인

![1. Deeplink 진입점 확인](../images/02-weak-host-validation-check/01-manifest-webview-entrypoint.png)

`AndroidManifest.xml` 분석 결과, `WebViewActivity`는 `VIEW` 및 `BROWSABLE` 인텐트 필터와 `scheme`, `host`를 함께 선언하고 있어 외부 URI 기반 deeplink 진입점으로 동작함을 확인할 수 있다. 반면 `WebView2Activity`는 custom action만 존재하여 이번 이슈의 직접적인 분석 대상에서는 제외하였다.

### 2. `/web`와 `/webview` 경로 처리 코드 확인

![2. `/web`와 `/webview` 경로 처리 코드 확인](../images/02-weak-host-validation-check/02-webview-path-validation-code.png)

`WebViewActivity` 내부에서는 `intent.getData()`로 전달된 URI를 기준으로 `/web`와 `/webview` 경로를 분기한다. 이 과정에서 `/web`는 별도 검증 없이 `url` 파라미터를 로드하고, `/webview`는 `endsWith("insecureshopapp.com")` 방식의 약한 문자열 비교로만 검증한 뒤 `webview.loadUrl(data)`를 호출한다.

### 3. `/web` 분기로 임의 URL 로드 확인

사용 명령:

```powershell
nox_adb shell am start -W -a android.intent.action.VIEW -d "insecureshop://com.insecureshop/web?url=https%3A%2F%2Fnaver.com" com.insecureshop
```

![3. `/web` 분기로 임의 URL 로드 확인](../images/02-weak-host-validation-check/03-web-deeplink-load-naver.png)

`nox_adb shell am start` 명령으로 `insecureshop://com.insecureshop/web?url=https://naver.com` deeplink를 호출한 결과, `WebViewActivity`가 실행되며 `naver.com`이 앱 내부 WebView에 로드되는 것을 확인하였다. 이는 `/web` 경로에서 외부 입력 URL이 충분한 검증 없이 로드됨을 보여준다.

### 4. `/webview` 분기의 약한 검증 우회 확인

사용 명령:

```powershell
nox_adb shell am start -W -a android.intent.action.VIEW -d "insecureshop://com.insecureshop/webview?url=https%3A%2F%2Fnaver.com%2F%3Fq%3Dinsecureshopapp.com" com.insecureshop
```

![4. `/webview` 분기의 약한 검증 우회 확인](../images/02-weak-host-validation-check/04-webview-bypass-load-naver.png)

`insecureshop://com.insecureshop/webview?url=https://naver.com/?q=insecureshopapp.com` 형태의 deeplink를 호출한 결과, 실제 host는 `naver.com`이지만 URL 문자열 끝이 `insecureshopapp.com`으로 끝난다는 이유로 검증을 통과하여 WebView가 로드되었다. 이는 host 기반 검증이 아닌 suffix 비교만 수행하는 약한 검증이 우회될 수 있음을 보여준다.
