# InsecureShop - Lack of SSL Certificate Validation

## 1. 개요

`InsecureShop`를 분석하던 중 `WebViewActivity`에서 사용하는 커스텀 `WebViewClient`가 SSL 인증서 오류를 안전하게 처리하지 않는 구조를 확인하였다. 일반적으로 WebView에서 인증서 오류가 발생하면 연결을 중단해야 하지만, 이 앱의 `CustomWebViewClient`는 `onReceivedSslError()`에서 `handler.proceed()`를 호출해 오류가 발생한 HTTPS 연결을 계속 진행한다.

이 구현은 신뢰할 수 없는 인증서, 만료된 인증서, 호스트명이 일치하지 않는 인증서 등을 WebView가 그대로 허용하게 만든다. 따라서 공격자가 네트워크 중간자 위치에서 변조된 인증서를 제시하더라도 WebView가 연결을 차단하지 않을 수 있으며, WebView에 로드되는 트래픽이 도청 또는 변조될 수 있다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Lack of SSL Certificate Validation` |
| 취약점 유형 | WebView SSL 오류 무시 |
| 영향 | 신뢰할 수 없는 인증서가 제시되어도 WebView가 연결을 계속 진행하여 트래픽 도청 또는 변조 가능 |
| 분석 도구 | `APK Easy Tool`, `jadx`, `adb` |
| 핵심 컴포넌트 | `WebViewActivity`, `CustomWebViewClient` |
| 검증 URL | `https://self-signed.badssl.com/` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | `Android` |
| 정적 분석 | `APK Easy Tool`, `jadx` |
| 동적 검증 | `adb` |
| 검증 대상 컴포넌트 | `com.insecureshop.WebViewActivity` |

## 4. 분석 방법

이번 항목은 WebView가 SSL 인증서 오류를 안전하게 처리하는지 확인하기 위해 다음 순서로 분석하였다.

1. `AndroidManifest.xml`에서 `WebViewActivity`가 딥링크로 실행 가능한지 확인하였다.
2. `WebViewActivity`에서 어떤 `WebViewClient`를 등록하는지 확인하였다.
3. `CustomWebViewClient.onReceivedSslError()` 구현을 확인하였다.
4. `self-signed.badssl.com`을 딥링크 URL로 전달해 WebView에 로드하였다.
5. SSL 오류가 발생해야 하는 페이지가 차단되지 않고 로드되는지 확인하였다.

## 5. 상세 분석

### 5.1 `WebViewActivity` 딥링크 진입점

Manifest를 확인한 결과 `WebViewActivity`는 `VIEW` 액션과 `BROWSABLE` 카테고리를 가진 딥링크 진입점으로 등록되어 있었다.

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

이 설정으로 인해 외부에서 아래와 같은 딥링크를 통해 `WebViewActivity`를 실행할 수 있다.

```text
insecureshop://com.insecureshop/web?url=...
```

### 5.2 `CustomWebViewClient` 등록

`WebViewActivity` 내부 구현을 확인한 결과, WebView에 기본 `WebViewClient`가 아닌 `CustomWebViewClient`가 등록되어 있었다.

```java
webview.setWebViewClient(new CustomWebViewClient());
```

따라서 WebView에서 발생하는 SSL 오류는 `CustomWebViewClient`의 `onReceivedSslError()` 구현에 의해 처리된다.

### 5.3 `onReceivedSslError()`에서 SSL 오류 무시

`CustomWebViewClient` 구현을 확인한 결과, SSL 인증서 오류가 발생했을 때 `handler.proceed()`를 호출하고 있었다.

```java
public final class CustomWebViewClient extends WebViewClient {
    @Override
    public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
        if (handler != null) {
            handler.proceed();
        }
    }
}
```

`handler.proceed()`는 SSL 오류가 발생했더라도 로드를 계속 진행하겠다는 의미다. 안전한 구현에서는 인증서 오류 발생 시 `handler.cancel()`로 연결을 중단해야 한다.

따라서 이 구현은 다음과 같은 인증서 오류를 WebView가 그대로 허용하게 만든다.

- self-signed 인증서
- 만료된 인증서
- 호스트명이 일치하지 않는 인증서
- 신뢰할 수 없는 CA가 발급한 인증서

### 5.4 `/web` 경로를 사용한 이유

`WebViewActivity`는 딥링크 경로에 따라 URL 처리 방식이 달랐다. `/webview` 경로는 `url` 파라미터가 `insecureshopapp.com`으로 끝나는지 확인하지만, `/web` 경로는 전달된 `url` 파라미터를 그대로 `loadUrl()`로 전달한다.

따라서 SSL 오류 재현에서는 다음 형태의 딥링크를 사용하였다.

```text
insecureshop://com.insecureshop/web?url=https://self-signed.badssl.com/
```

## 6. 영향

이 취약점을 악용하면 공격자는 네트워크 중간자 위치에서 WebView 트래픽을 도청하거나 변조할 수 있다. 사용자가 공용 Wi-Fi, 프록시, 악성 네트워크 환경에 연결된 경우 공격자는 신뢰할 수 없는 인증서를 제시하더라도 WebView가 이를 차단하지 않도록 만들 수 있다.

실제 서비스 환경에서 동일한 구성이 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- WebView에 로드되는 HTTPS 트래픽 도청 가능
- WebView 페이지 내용 변조 가능
- 로그인 토큰, 세션 정보, 개인정보 등 민감 데이터 노출 가능
- 피싱 페이지 또는 악성 스크립트 삽입 가능
- SSL/TLS 기반 서버 신뢰 검증 우회

이번 검증에서는 self-signed 인증서 페이지 로드까지만 확인했으며, 실제 트래픽 탈취나 변조 행위는 수행하지 않았다.

## 7. 대응 방안

- `onReceivedSslError()`에서 `handler.proceed()`를 호출하지 않아야 한다.
- SSL 오류 발생 시 `handler.cancel()`로 연결을 중단해야 한다.
- 가능하면 `onReceivedSslError()`를 오버라이드하지 않고 WebView 기본 SSL 검증 동작을 사용해야 한다.
- 개발 또는 테스트 목적으로 임시 허용이 필요하더라도 릴리즈 빌드에는 포함하지 않아야 한다.
- 인증서 오류 발생 시 사용자에게 민감한 선택지를 직접 제공하기보다 안전하게 차단하는 정책을 적용해야 한다.
- HTTPS 통신에는 정상적으로 신뢰 가능한 CA가 발급한 인증서를 사용해야 한다.

안전한 구현 예시는 다음과 같다.

```java
@Override
public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
    if (handler != null) {
        handler.cancel();
    }
}
```

또는 해당 메서드를 아예 제거해 WebView 기본 동작을 따르는 것이 바람직하다.

## 8. 정리

이번 분석에서는 `WebViewActivity`가 딥링크를 통해 외부 URL을 WebView에 로드할 수 있고, 해당 WebView에 `CustomWebViewClient`가 등록되어 있음을 확인하였다. 이어서 `CustomWebViewClient.onReceivedSslError()`가 SSL 인증서 오류 발생 시 `handler.cancel()`이 아닌 `handler.proceed()`를 호출하고 있음을 확인하였다.

최종적으로 `https://self-signed.badssl.com/`을 딥링크로 전달해 WebView에 로드한 결과, self-signed 인증서 오류가 발생해야 하는 페이지가 차단되지 않고 표시되었다.

따라서 이번 항목은 **SSL 인증서 오류를 무시하고 WebView 로드를 계속 진행하는 `Lack of SSL Certificate Validation` 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

### 1. WebViewActivity 딥링크 설정 확인

![WebViewActivity 딥링크 설정 확인](../images/16-Lack%20of%20SSL%20Certificate%20Validation/01-webviewactivity-deeplink.png)

`WebViewActivity`는 `VIEW`, `DEFAULT`, `BROWSABLE` intent-filter와 `insecureshop://com.insecureshop` 딥링크를 통해 외부에서 실행할 수 있었다.

### 2. CustomWebViewClient 등록 확인

![WebViewActivity에서 CustomWebViewClient 등록 확인](../images/16-Lack%20of%20SSL%20Certificate%20Validation/02-set-custom-webviewclient.png)

`WebViewActivity`는 WebView에 `CustomWebViewClient`를 등록하고 있었다. 따라서 SSL 오류 처리 흐름은 이 클래스의 구현을 따른다.

### 3. handler.proceed() 호출 확인

![CustomWebViewClient에서 handler.proceed 호출 확인](../images/16-Lack%20of%20SSL%20Certificate%20Validation/03-handler-proceed.png)

`CustomWebViewClient.onReceivedSslError()`는 SSL 오류 발생 시 `handler.cancel()`이 아니라 `handler.proceed()`를 호출한다. 이 코드가 WebView SSL 검증 우회의 핵심이다.

### 4. self-signed 인증서 페이지 로드 명령 실행

![self-signed.badssl.com 로드 명령 실행](../images/16-Lack%20of%20SSL%20Certificate%20Validation/05-self-signed-command.png)

다음 명령으로 `WebViewActivity`에 `https://self-signed.badssl.com/` URL을 전달하였다.

```powershell
nox_adb shell am start -W -n com.insecureshop/.WebViewActivity -a android.intent.action.VIEW -d "insecureshop://com.insecureshop/web?url=https%3A%2F%2Fself-signed.badssl.com%2F"
```

실행 결과 `Status: ok`와 함께 `Activity: com.insecureshop/.WebViewActivity`가 확인되었다.

### 5. self-signed.badssl.com 페이지 로드 확인

![self-signed.badssl.com 페이지가 WebView에 로드된 화면](../images/16-Lack%20of%20SSL%20Certificate%20Validation/04-self-signed-loaded.png)

`self-signed.badssl.com`은 신뢰할 수 없는 self-signed 인증서를 사용하는 테스트 페이지다. 정상적인 SSL 검증 흐름이라면 WebView는 인증서 오류를 감지하고 연결을 중단해야 한다. 그러나 InsecureShop의 WebView는 `handler.proceed()` 호출로 인해 해당 페이지를 그대로 표시하였다.
