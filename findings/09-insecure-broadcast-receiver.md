# InsecureShop - Insecure Broadcast Receiver

## 1. 개요

`InsecureShop`를 분석하던 중 `AboutUsActivity`가 `exported=true` 상태로 외부에서 실행 가능하다는 점을 확인하였다. 처음에는 단순한 정보성 화면처럼 보였지만, `onCreate()`를 따라가 보니 이 Activity는 실행 직후 `CustomReceiver`를 동적으로 등록하고 있었고, 해당 리시버는 외부 브로드캐스트에서 전달된 `web_url` 값을 읽어 `WebView2Activity`를 실행하도록 구성되어 있었다.

즉 구조를 단계별로 정리하면 다음과 같다.

1. 외부에서 `AboutUsActivity`를 실행
2. `AboutUsActivity`가 `CustomReceiver`를 등록
3. 외부에서 `com.insecureshop.CUSTOM_INTENT` 브로드캐스트 전송
4. `CustomReceiver`가 `web_url` 값을 읽음
5. `WebView2Activity`를 열고 `url` extra에 해당 값을 넣음
6. `WebView2Activity`가 그 값을 `webview.loadUrl()`에 전달

이로 인해 공격자는 `AboutUsActivity`가 활성화된 상태에서 crafted broadcast를 보내는 것만으로 앱 내부 WebView에 임의 URL을 띄울 수 있다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Insecure Broadcast Receiver` |
| 취약점 유형 | 동적으로 등록된 BroadcastReceiver가 외부 입력을 검증 없이 WebView 실행으로 연결 |
| 영향 | 외부 앱 또는 `adb`를 통해 앱 내부 WebView에 임의 URL을 로드할 수 있음 |
| 분석 도구 | `jadx`, `nox_adb`, `Nox` |
| 핵심 컴포넌트 | `AboutUsActivity`, `CustomReceiver`, `WebView2Activity` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | Android |
| 정적 분석 | `jadx` |
| 동적 검증 | `nox_adb shell am start`, `nox_adb shell am broadcast` |

## 4. 분석 방법

이번 항목은 “외부 broadcast가 앱 내부 WebView 로딩까지 이어지는지”를 기준으로 다음 순서로 분석하였다.

1. `AndroidManifest.xml`에서 `AboutUsActivity`가 외부에서 실행 가능한지 확인하였다.
2. `AboutUsActivity.onCreate()`에서 `CustomReceiver`를 동적으로 등록하는지 확인하였다.
3. `CustomReceiver.onReceive()`가 외부 입력을 어떻게 처리하는지 분석하였다.
4. `WebView2Activity`가 `url` extra를 실제로 `loadUrl()`에 전달하는지 확인하였다.
5. `AboutUsActivity`를 먼저 실행한 뒤, `CUSTOM_INTENT` 브로드캐스트를 보내 임의 URL이 WebView에 로드되는지 검증하였다.

## 5. 상세 분석

### 5.1 왜 `AboutUsActivity`를 먼저 봤는가

`AndroidManifest.xml`을 확인한 결과 `AboutUsActivity`는 아래와 같이 `exported=true` 상태였다.

```xml
<activity
    android:name="com.insecureshop.AboutUsActivity"
    android:exported="true"/>
```

이 설정의 의미는 외부 앱이나 `adb`가 `AboutUsActivity`를 직접 실행할 수 있다는 것이다.  
처음에는 단순한 “소개 화면”처럼 보이지만, 외부에서 실행 가능한 Activity는 내부에서 어떤 부가 동작을 하는지 꼭 확인해야 한다. 실제로 이번 항목에서도 핵심은 Activity 화면 자체가 아니라, **그 Activity가 열릴 때 같이 등록되는 BroadcastReceiver**였다.

### 5.2 `AboutUsActivity`는 실행 시점에 `CustomReceiver`를 등록함

`AboutUsActivity.onCreate()`를 보면 아래와 같은 코드가 존재한다.

```java
CustomReceiver customReceiver = new CustomReceiver();
this.receiver = customReceiver;
registerReceiver(customReceiver, new IntentFilter("com.insecureshop.CUSTOM_INTENT"));
```

코드 흐름을 순서대로 보면 다음과 같다.

- `AboutUsActivity`가 열리면 `CustomReceiver` 객체를 하나 만들고
- 액션이 `com.insecureshop.CUSTOM_INTENT`인 broadcast를 받도록 등록한다.

즉 이 receiver는 앱이 실행되는 내내 항상 살아 있는 것이 아니라, **`AboutUsActivity`가 열려 있을 때만 활성화되는 동적 리시버**다. 그래서 재현에서도 `AboutUsActivity`를 먼저 실행해야 했다.

### 5.3 `CustomReceiver`는 `web_url` 값을 받아 `WebView2Activity`를 실행함

`CustomReceiver.onReceive()`를 분석한 결과, 리시버는 브로드캐스트에서 `web_url` 값을 꺼낸 뒤 `WebView2Activity`를 실행하고 있었다.

```java
String stringExtra = extras.getString("web_url");
if (!(str == null || StringsKt.isBlank(str))) {
    Intent intent2 = new Intent(context, (Class<?>) WebView2Activity.class);
    intent2.putExtra("url", stringExtra);
    context.startActivity(intent2);
}
```

즉 외부에서 전달한 `web_url`이 비어있지 않으면:

1. `WebView2Activity`를 실행할 Intent를 만들고
2. `url` extra에 외부 값을 넣고
3. 바로 `startActivity()`를 호출한다.

여기에는 발신자 검증, 도메인 검증, 허용 URL 확인 같은 방어 로직이 없다. 그래서 외부 입력이 그대로 다음 단계로 전달된다.

### 5.4 `WebView2Activity`는 `url` extra를 그대로 `loadUrl()`에 넘김

`WebView2Activity`를 확인해보면 여러 입력 경로 중 하나로 `url` extra를 읽고, 최종적으로 `webview.loadUrl()`에 전달하는 분기가 존재한다.

```java
Bundle extras = intent5.getExtras();
String string = extras != null ? extras.getString("url") : null;
...
webview.loadUrl(extras2 != null ? extras2.getString("url") : null);
```

즉 `CustomReceiver`가 넣은:

```java
intent2.putExtra("url", stringExtra);
```

값이 그대로 `WebView2Activity`에 전달되고, 최종적으로 앱 내부 WebView에서 로드된다.

정리하면 전체 흐름은 다음과 같다.

1. 외부에서 `AboutUsActivity` 실행
2. `CustomReceiver` 등록
3. 외부에서 `CUSTOM_INTENT` broadcast 전송
4. `web_url` 추출
5. `WebView2Activity`에 `url` extra로 전달
6. `webview.loadUrl(url)` 실행

### 5.5 왜 `am`으로 재현이 쉬웠는가

이번 항목은 입력 구조가 단순했다.

- 액션 문자열: `com.insecureshop.CUSTOM_INTENT`
- 문자열 extra: `web_url`

즉 nested `Intent`나 custom `Parcelable`이 필요한 구조가 아니어서, `adb am broadcast`만으로도 재현이 가능했다. 다만 receiver가 동적으로 등록되는 구조이기 때문에, **먼저 `AboutUsActivity`를 실행해야 한다는 조건**은 있었다.

### 5.6 왜 이게 취약점인가

이번 문제의 핵심은 “브로드캐스트를 받는다” 자체가 아니라, **외부 broadcast가 그대로 위험 동작으로 연결된다**는 점이다.

원래 안전하려면 다음 중 하나가 필요하다.

- 브로드캐스트 발신자 검증
- 권한 기반 제한
- 허용된 URL만 처리하는 allowlist 검증
- 내부 전용으로만 사용하는 구조

하지만 현재 구조는:

- 외부에서 `AboutUsActivity`를 실행할 수 있고
- Activity가 열리면 `CustomReceiver`가 등록되고
- 외부 `web_url` 값을 그대로 받아
- `WebView2Activity`를 통해 앱 내부 WebView에 로드한다.

즉 공격자는 임의 URL을 앱 내부 브라우저 신뢰 영역 안에서 띄울 수 있으며, 이는 피싱 페이지 노출이나 기존 WebView 취약점과의 결합 위험으로 이어질 수 있다.

## 6. 동적 검증

### 6.1 `AboutUsActivity` 활성화

동적 리시버는 `AboutUsActivity`가 열려 있을 때만 등록되므로, 먼저 아래 명령으로 `AboutUsActivity`를 실행하였다.

```powershell
nox_adb shell am start -n com.insecureshop/.AboutUsActivity
```

### 6.2 crafted broadcast 전송

이후 아래 명령으로 `web_url` 값을 포함한 브로드캐스트를 전송하였다.

```powershell
nox_adb shell am broadcast -a com.insecureshop.CUSTOM_INTENT --es web_url "https://github.com/sangrok-jeon/insecureshop-android-security-analysis"
```

### 6.3 검증 결과

브로드캐스트 전송 후 `WebView2Activity`가 열리며, 앱 내부 WebView에서 지정한 GitHub URL이 실제로 로드되었다.  
즉 외부 broadcast의 `web_url` 값이 `CustomReceiver`와 `WebView2Activity`를 거쳐 그대로 `loadUrl()`에 도달했음을 동적으로 확인하였다.

## 7. 영향도

이 구조를 악용하면 동일 기기에 설치된 악성 앱이나 `adb` 명령을 통해 `AboutUsActivity`가 활성화된 시점에 crafted broadcast를 보내, 앱 내부 WebView에 임의 URL을 로드하게 만들 수 있다. 실제 서비스 환경에서 이와 같은 구조가 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- 사용자가 신뢰하는 앱 내부 화면에서 외부 페이지가 열릴 수 있다.
- 피싱 페이지, 위장 로그인 페이지, 악성 웹 콘텐츠 노출이 가능하다.
- 기존 WebView 관련 취약점과 결합될 경우 추가 공격으로 이어질 수 있다.

즉 이번 문제는 단순한 브로드캐스트 수신 문제가 아니라, **외부 입력이 앱 내부 WebView 신뢰 영역까지 그대로 연결되는 구조**라는 점에서 위험하다.

## 8. 대응 방안

- 동적으로 등록한 BroadcastReceiver에 대해 발신자 검증 또는 권한 제한을 추가해야 한다.
- 외부에서 전달된 `web_url` 값을 그대로 `startActivity()`와 `loadUrl()`로 넘기지 않아야 한다.
- `WebView2Activity`가 로드할 수 있는 URL에 대해 allowlist 기반 검증을 적용해야 한다.
- 불필요한 `exported` Activity는 외부 노출을 제거하거나, 외부 진입점과 내부 로직을 분리해야 한다.

## 9. 결론

이번 분석에서는 `AboutUsActivity`가 `exported=true` 상태로 외부에 노출되어 있으며, 실행 시점에 `CustomReceiver`를 동적으로 등록한다는 점을 확인하였다. 또한 `CustomReceiver`가 외부 broadcast의 `web_url` 값을 검증 없이 `WebView2Activity`의 `url` extra로 전달하고, `WebView2Activity`가 이를 그대로 `webview.loadUrl()`에 넘기는 구조를 확인하였다.

추가로 `am start`와 `am broadcast`를 이용한 동적 검증 결과, 외부에서 전달한 GitHub URL이 실제로 앱 내부 WebView에 로드되었다. 이를 통해 9번 항목은 **동적 broadcast receiver를 통해 임의 URL 로딩이 가능한 `Insecure Broadcast Receiver` 취약점**으로 정리할 수 있었다.

## 10. 취약점 테스트

### 1. AboutUsActivity 외부 진입점 확인

![1. AboutUsActivity 외부 진입점 확인](../images/09-Insecure%20Broadcast%20Receiver/01-aboutus-manifest.png)

`AboutUsActivity`는 `android:exported="true"` 상태로 선언되어 있어 외부에서 직접 실행할 수 있다. 이번 항목에서는 이 Activity가 단순 소개 화면이 아니라, 동적 receiver 등록의 진입점이라는 점이 중요했다.

### 2. AboutUsActivity가 `CUSTOM_INTENT` receiver를 동적으로 등록하는 코드 확인

![2. AboutUsActivity가 CUSTOM_INTENT receiver를 동적으로 등록하는 코드 확인](../images/09-Insecure%20Broadcast%20Receiver/02-aboutus-registerreceiver.png)

`AboutUsActivity.onCreate()`는 `CustomReceiver`를 생성하고, 액션이 `com.insecureshop.CUSTOM_INTENT`인 broadcast를 받도록 `registerReceiver(...)`를 호출한다. 이 코드가 9번 취약점의 시작점이다.

### 3. CustomReceiver가 `web_url` 값을 받아 WebView2Activity를 실행하는 코드 확인

![3. CustomReceiver가 web_url 값을 받아 WebView2Activity를 실행하는 코드 확인](../images/09-Insecure%20Broadcast%20Receiver/03-customreceiver-onreceive.png)

`CustomReceiver.onReceive()`는 `extras.getString("web_url")`로 외부 값을 읽고, 이를 `url` extra로 넣은 뒤 `WebView2Activity`를 실행한다. 즉 외부 broadcast 입력이 내부 Activity 실행으로 이어진다.

### 4. WebView2Activity가 `url` extra를 그대로 `loadUrl()`에 전달하는 코드 확인

![4. WebView2Activity가 url extra를 그대로 loadUrl()에 전달하는 코드 확인](../images/09-Insecure%20Broadcast%20Receiver/05-webview2-loadurl-extra.png)

`WebView2Activity`는 전달받은 `url` extra를 그대로 `webview.loadUrl()`에 넘긴다. 이로 인해 broadcast에서 전달된 값이 최종적으로 앱 내부 WebView에 로드된다.

### 5. 일반 UI에서도 About 화면으로 진입 가능한 모습

![5. 일반 UI에서도 About 화면으로 진입 가능한 모습](../images/09-Insecure%20Broadcast%20Receiver/06-about-menu-entry.png)

앱 UI 상에서도 상단 메뉴를 통해 `About` 화면에 접근할 수 있었다. 즉 사용자가 정상적으로 `AboutUsActivity`를 열어둔 상태에서도 동적 receiver가 활성화될 수 있다.

### 6. `am start`로 AboutUsActivity를 직접 실행한 모습

![6. am start로 AboutUsActivity를 직접 실행한 모습](../images/09-Insecure%20Broadcast%20Receiver/07-am-start-aboutusactivity.png)

동적 receiver를 활성화하기 위해 먼저 `nox_adb shell am start -n com.insecureshop/.AboutUsActivity` 명령을 사용해 `AboutUsActivity`를 직접 실행하였다.

### 7. `am broadcast`로 `CUSTOM_INTENT`와 `web_url` 값을 전송한 모습

![7. am broadcast로 CUSTOM_INTENT와 web_url 값을 전송한 모습](../images/09-Insecure%20Broadcast%20Receiver/08-am-broadcast-custom-intent.png)

이후 `nox_adb shell am broadcast -a com.insecureshop.CUSTOM_INTENT --es web_url "https://github.com/sangrok-jeon/insecureshop-android-security-analysis"` 명령으로 crafted broadcast를 전송하였다.

### 8. 앱 내부 WebView에서 임의 URL이 실제로 로드된 모습

![8. 앱 내부 WebView에서 임의 URL이 실제로 로드된 모습](../images/09-Insecure%20Broadcast%20Receiver/09-webview-load-result.png)

브로드캐스트 전송 후 `WebView2Activity`가 열리며, 앱 내부 WebView에서 지정한 GitHub 저장소 URL이 실제로 로드되었다. 이를 통해 9번 취약점이 동적으로 재현되었음을 확인하였다.
