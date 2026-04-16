# InsecureShop - Intercepting Implicit intent to load arbitrary URL

## 1. 개요

`InsecureShop`를 분석하던 중 상품 목록의 `More Info` 버튼 클릭이 내부적으로 브로드캐스트를 발생시키고, 이후 `BroadcastReceiver`가 암시적 인텐트(`implicit intent`)로 Activity를 실행하는 구조를 확인하였다. 내부 동작에 가까운 Activity 호출은 명시적 인텐트(`explicit intent`)로 제한하는 것이 바람직하지만, 이 앱은 `com.insecureshop.action.WEBVIEW` 액션만 지정한 인텐트로 `startActivity()`를 수행하고 있었다.

외부 앱이 동일한 action을 처리하는 Activity를 등록하면 chooser에 함께 나타날 수 있고, 사용자가 공격 앱을 선택할 경우 원래 `InsecureShop`가 전달하려던 `url` 값을 제3자 앱이 가로챌 수 있다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Intercepting Implicit intent to load arbitrary URL` |
| 취약점 유형 | 암시적 인텐트를 통한 Activity Hijacking |
| 영향 | 외부 앱이 동일 action을 등록해 Activity 실행 흐름을 가로채고 전달된 `url` 값을 수신할 수 있음 |
| 분석 도구 | `jadx`, `Android Studio`, `adb` |
| 핵심 컴포넌트 | `ProductAdapter`, `ProductListActivity`, `ProductDetailBroadCast`, `WebView2Activity` |
| 검증 데이터 | `url = https://www.insecureshopapp.com/` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | `Android` |
| 정적 분석 | `jadx` |
| 동적 검증 | `Android Studio`, `PoC App`, `adb` |
| 검증 대상 액션 | `com.insecureshop.action.PRODUCT_DETAIL`, `com.insecureshop.action.WEBVIEW` |

## 4. 분석 방법

이번 항목은 `More Info` 클릭 이후 Activity 실행이 어떤 방식으로 이루어지는지를 기준으로 다음 순서로 분석하였다.

1. `ProductAdapter`에서 `More Info` 클릭 시 어떤 인텐트가 생성되는지 확인하였다.
2. `ProductListActivity`에서 `PRODUCT_DETAIL` 브로드캐스트를 수신하는 리시버가 어떻게 등록되는지 확인하였다.
3. `ProductDetailBroadCast.onReceive()`가 수신 후 어떤 Activity 실행 흐름으로 이어지는지 확인하였다.
4. `AndroidManifest.xml`에서 `com.insecureshop.action.WEBVIEW`를 처리하는 Activity를 확인하였다.
5. 별도 `PoC App`에 동일 action을 처리하는 Activity를 등록하였다.
6. `InsecureShop`에서 `More Info`를 클릭한 뒤 chooser와 PoC 화면, `logcat`을 통해 intent hijacking이 가능한지 검증하였다.

## 5. 상세 분석

### 5.1 `More Info` 클릭 시 `PRODUCT_DETAIL` 브로드캐스트 전송

`ProductAdapter` 코드를 확인한 결과, 상품 목록의 `More Info` 클릭 시 `com.insecureshop.action.PRODUCT_DETAIL` 액션을 갖는 브로드캐스트가 전송되고 있었다.

```java
Intent intent = new Intent("com.insecureshop.action.PRODUCT_DETAIL");
intent.putExtra("url", prodDetail.getUrl());
context.sendBroadcast(intent);
```

즉 `More Info` 클릭은 직접 `WebView`를 여는 것이 아니라, 먼저 `PRODUCT_DETAIL` 브로드캐스트를 발생시키는 구조였다.

### 5.2 `ProductListActivity`가 동적 리시버를 등록

`ProductListActivity`를 확인한 결과, `onCreate()`에서 `ProductDetailBroadCast`를 런타임에 등록하고 있었다.

```java
IntentFilter intentFilter = new IntentFilter("com.insecureshop.action.PRODUCT_DETAIL");
registerReceiver(this.productDetailBroadCast, intentFilter);
```

`ProductDetailBroadCast`는 `AndroidManifest.xml`에 선언된 정적 리시버가 아니라, `ProductListActivity`가 실행 중일 때만 동적으로 등록되는 리시버다. 따라서 `More Info` 클릭으로 전송된 `PRODUCT_DETAIL` 브로드캐스트는 현재 실행 중인 `ProductListActivity`가 등록한 `ProductDetailBroadCast`가 수신하게 된다.

### 5.3 `ProductDetailBroadCast`가 암시적 인텐트로 Activity 실행

`ProductDetailBroadCast.onReceive()`를 확인한 결과, 브로드캐스트를 수신한 뒤 `com.insecureshop.action.WEBVIEW` 액션을 갖는 새 인텐트를 생성해 `startActivity()`를 호출하고 있었다.

```java
Intent webViewIntent = new Intent("com.insecureshop.action.WEBVIEW");
webViewIntent.putExtra("url", "https://www.insecureshopapp.com/");
if (context != null) {
    context.startActivity(webViewIntent);
}
```

여기서 핵심은 다음과 같다.

- `startActivity()`가 explicit intent가 아니라 action 기반 implicit intent로 수행됨
- 수신 대상 컴포넌트를 명시하지 않음
- 외부 앱이 동일 action을 처리하는 Activity를 등록하면 chooser에 함께 나타날 수 있음

또한 처음 `ProductAdapter`에서 `prodDetail.getUrl()`을 담아 브로드캐스트를 보내지만, 실제 `ProductDetailBroadCast`에서는 이 값을 사용하지 않고 `https://www.insecureshopapp.com/`로 덮어쓰고 있었다. 따라서 최종적으로 외부 앱이 가로채는 값도 제품별 URL이 아니라 하드코딩된 URL이다.

### 5.4 `WEBVIEW` 액션을 처리하는 기본 Activity

`AndroidManifest.xml`을 확인한 결과, `com.insecureshop.action.WEBVIEW` 액션은 `WebView2Activity`가 처리하고 있었다.

```xml
<activity android:name="com.insecureshop.WebView2Activity">
    <intent-filter>
        <action android:name="com.insecureshop.action.WEBVIEW"/>
        <category android:name="android.intent.category.DEFAULT"/>
        <category android:name="android.intent.category.BROWSABLE"/>
    </intent-filter>
</activity>
```

즉 `ProductDetailBroadCast`가 호출하는 `startActivity(new Intent("com.insecureshop.action.WEBVIEW"))`는 원래 `WebView2Activity`로 연결되는 내부 흐름이었다. 그러나 이 호출이 implicit intent이기 때문에 동일 action을 등록한 외부 앱도 선택지에 포함될 수 있다.

## 6. 영향

이 구조를 악용하면 외부 앱이 동일 action을 등록하는 것만으로 내부 Activity 실행 흐름에 끼어들 수 있다. 특히 사용자가 chooser에서 공격 앱을 선택하면 원래 앱이 전달하려던 데이터를 외부 앱이 수신하게 되므로, 내부 전용으로 생각했던 흐름이 제3자 앱에 노출될 수 있다.

실제 서비스 환경에서 동일한 구성이 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- 내부 Activity 실행 흐름이 외부 앱에 의해 가로채질 수 있음
- intent extra로 전달되는 URL, 토큰, 식별자 등이 외부 앱으로 유출될 수 있음
- 사용자가 chooser를 통해 공격 앱을 선택하도록 유도되는 사회공학 공격이 가능할 수 있음
- 이후 외부 앱이 피싱 페이지, 변조된 화면, 추가 수집 로직으로 연결할 수 있음

이번 검증에서는 `url` 값 수신까지 확인했으며, 추가적인 페이지 변조나 계정 탈취 시도는 수행하지 않았다.

## 7. 대응 방안

- 내부 Activity 호출에는 implicit intent 대신 explicit intent를 사용해야 한다.
- `startActivity(new Intent("..."))` 형태 대신 대상 컴포넌트를 명시적으로 지정해야 한다.
- 외부 앱이 개입하면 안 되는 action 문자열 기반 호출은 제거하거나 내부 전용 구조로 대체해야 한다.
- intent extra에 민감 데이터 또는 내부 제어 값을 담아 전달하는 구조를 최소화해야 한다.
- 필요한 경우 패키지 제한, signature-level 보호, 비공개 컴포넌트 설계로 외부 개입을 차단해야 한다.
- chooser 노출이 보안상 문제가 되는 내부 흐름은 사용자 선택에 맡기지 않도록 재설계해야 한다.

## 8. 정리

이번 분석에서는 `ProductAdapter`의 `More Info` 클릭이 `PRODUCT_DETAIL` 브로드캐스트를 발생시키고, `ProductListActivity`가 런타임에 등록한 `ProductDetailBroadCast`가 이를 수신하는 구조를 확인하였다. 이어서 `ProductDetailBroadCast.onReceive()`는 `com.insecureshop.action.WEBVIEW` 액션을 갖는 암시적 인텐트를 생성해 `startActivity()`를 호출하고 있었으며, 이 호출은 특정 Activity를 명시하지 않는 형태였다.

최종적으로 별도 `PoC App`을 제작해 동일 action을 처리하는 Activity를 등록한 뒤 `More Info`를 클릭하자 chooser에 공격 앱이 함께 표시되었고, 사용자가 이를 선택했을 때 `url = https://www.insecureshopapp.com/` 값이 PoC 화면과 `logcat`에서 그대로 확인되었다.

따라서 이번 항목은 **암시적 인텐트로 Activity를 호출하는 구조로 인해, 제3자 앱이 실행 흐름을 가로채고 전달된 데이터를 수신할 수 있는 `Intercepting Implicit intent to load arbitrary URL` 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

### 1. 상품 목록 화면에서 More Info 클릭 지점 확인

![상품 목록 화면에서 More Info 클릭 지점 확인](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/01-more-info-click.png)

상품 목록에서 `More Info`를 클릭하면 `ProductAdapter`의 클릭 리스너가 실행된다.

### 2. PRODUCT_DETAIL 브로드캐스트 전송 코드 확인

![ProductAdapter에서 PRODUCT_DETAIL 브로드캐스트 전송 확인](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/02-productadapter-broadcast.png)

`More Info` 클릭 시 `com.insecureshop.action.PRODUCT_DETAIL` 브로드캐스트가 전송되고, `url` extra가 함께 포함된다.

### 3. PRODUCT_DETAIL 동적 리시버 등록 확인

![ProductListActivity에서 PRODUCT_DETAIL 리시버 등록 확인](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/03-productlist-registerreceiver.png)

`ProductListActivity`는 `registerReceiver()`를 통해 `ProductDetailBroadCast`를 동적으로 등록한다. 따라서 해당 브로드캐스트는 실행 중인 `ProductListActivity`의 리시버가 수신한다.

### 4. WEBVIEW action으로 startActivity 호출 확인

![ProductDetailBroadCast에서 WEBVIEW 액션으로 startActivity 호출 확인](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/04-productdetail-broadcast-onreceive.png)

`ProductDetailBroadCast`는 `com.insecureshop.action.WEBVIEW` 액션만 지정한 implicit intent로 Activity를 실행한다.

### 5. 기본 WebView 동작 확인

![기본 동작으로 Webview 화면이 열리는 모습](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/05-default-webview-open.png)

공격 앱이 없을 때는 기본적으로 InsecureShop의 WebView 화면이 열리고 `https://www.insecureshopapp.com/` 로딩을 시도한다.

### 6. PoC App 초기 화면

![PoC App 초기 화면](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/06-poc-initial-screen.png)

PoC 앱은 `com.insecureshop.action.WEBVIEW` 액션을 처리하는 Activity를 등록하고, 수신한 `url` 값을 화면과 로그에 출력하도록 구성하였다.

### 7. Chooser에서 공격 앱 노출 확인

![Chooser에서 webviewhijackpoc가 함께 표시되는 모습](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/07-chooser-hijack-app.png)

`More Info` 클릭 후 chooser에 원래 앱과 함께 `webviewhijackpoc`가 표시되었다. 이는 `WEBVIEW` 인텐트가 explicit하지 않기 때문에 제3자 앱도 후보로 노출될 수 있음을 보여준다.

### 8. PoC 앱에서 URL 수신 확인

![PoC 앱이 WEBVIEW 액션을 가로채고 url을 표시한 화면](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/08-poc-hijacked-result.png)

chooser에서 `webviewhijackpoc`를 선택하자 PoC 앱이 실행되었고, `url = https://www.insecureshopapp.com/` 값이 화면에 표시되었다.

### 9. logcat 기반 최종 검증

![WEBVIEW_HIJACK logcat 확인](../images/13-Intercepting%20Implicit%20intent%20to%20load%20arbitrary%20URL/09-logcat-webview-hijack.png)

`adb logcat`에서도 다음 값이 확인되었다.

```text
D WEBVIEW_HIJACK: Hijacked action = com.insecureshop.action.WEBVIEW
D WEBVIEW_HIJACK: Intercepted url = https://www.insecureshopapp.com/
```
