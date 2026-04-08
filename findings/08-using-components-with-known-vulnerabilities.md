# InsecureShop - Using Components with Known Vulnerabilities

## 1. 개요

`InsecureShop`를 분석하던 중 `AndroidManifest.xml`에 `net.gotev.uploadservice.UploadService`가 `exported=true` 상태로 선언된 것을 확인하였다. 해당 서비스는 앱이 직접 구현한 컴포넌트가 아니라 `android-upload-service` 계열의 서드파티 업로드 라이브러리이며, 외부 앱이 직접 호출할 수 있는 구조였다.

정적 분석 결과 이 서비스는 외부 `Intent`로부터 업로드 작업 클래스(`taskClass`)와 업로드 파라미터(`taskParameters`, `httpTaskParameters`)를 전달받아 업로드를 수행할 수 있었다. 특히 `taskParameters` 내부에는 업로드 대상 파일 목록(`files`)과 업로드 목적지 URL(`serverUrl`)이 포함되어 있었고, 실제 업로드 구현체는 지정된 파일을 읽어 지정된 원격 URL로 전송하도록 구성되어 있었다.

이번 항목은 단순히 “앱에 파일 업로드 버튼이 있느냐”를 보는 문제가 아니라, **앱 내부에 포함된 취약한 서드파티 업로드 컴포넌트가 외부에 노출되어 있어 앱 로컬 파일 유출에 악용될 수 있는지**를 검증하는 문제로 접근하였다. 추가로 별도 `PoC App`을 제작해 취약 라이브러리 버전을 포함한 뒤, `InsecureShop`의 `UploadService`를 직접 호출하는 방식으로 앱 내부 `Prefs.xml`이 외부 수신 서버로 전달되는 것을 확인하였다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Using Components with Known Vulnerabilities` |
| 취약점 유형 | 취약한 third-party upload service의 외부 노출 및 로컬 파일 외부 전송 |
| 영향 | 동일 기기의 외부 앱이 `InsecureShop` 내부 파일을 임의 원격 도메인으로 전송할 수 있음 |
| 분석 도구 | `jadx`, `Android Studio`, `PoC App`, 로컬 수신 서버 |
| 핵심 컴포넌트 | `net.gotev.uploadservice.UploadService` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | Android |
| 정적 분석 | `jadx` |
| 동적 검증 | `Android Studio`, 별도 `PoC App`, 로컬 HTTP 수신 서버 |

## 4. 분석 방법

이번 항목은 “취약한 서드파티 업로드 컴포넌트가 실제로 로컬 파일 유출에 악용될 수 있는지”를 기준으로 다음 순서로 분석하였다.

1. `AndroidManifest.xml`에서 `net.gotev.uploadservice.UploadService`가 외부에 노출되어 있는지 확인하였다.
2. `UploadService`, `UploadTask`, `UploadTaskParameters`, `UploadFile`, `MultipartUploadTask`, `HttpUploadTask`를 따라가며 외부 입력이 어떤 방식으로 업로드 흐름에 연결되는지 분석하였다.
3. `files`, `serverUrl`, `path`가 각각 업로드 대상 파일과 원격 목적지를 의미하는지 확인하였다.
4. 별도 `PoC App`에 취약한 라이브러리 버전을 포함하고, `InsecureShop`의 `UploadService`를 직접 호출하는 구조를 구성하였다.
5. `Prefs.xml`을 대상으로 전송을 시도한 뒤, 로컬 HTTP 수신 서버에서 앱 내부 설정 파일 내용이 실제로 수신되는지 확인하였다.

## 5. 상세 분석

### 5.1 왜 `UploadService`를 먼저 의심했는가

`AndroidManifest.xml`을 확인한 결과 `InsecureShop`에는 아래와 같이 외부 업로드 라이브러리 서비스가 포함되어 있었다.

```xml
<service
    android:name="net.gotev.uploadservice.UploadService"
    android:enabled="true"
    android:exported="true"/>
```

이 설정은 다음을 의미한다.

- `net.gotev.uploadservice.UploadService`
  - `InsecureShop` 개발자가 직접 작성한 코드가 아니라, 외부 업로드 라이브러리 컴포넌트
- `enabled=true`
  - 서비스가 비활성화되지 않았으며 사용 가능한 상태
- `exported=true`
  - 동일 기기에 설치된 다른 앱이 이 서비스를 직접 호출할 수 있음

즉 앱 UI에 별도 업로드 기능이 보이지 않더라도, 구조상 외부 앱이 접근 가능한 업로드 엔진이 앱 내부에 존재하는 상태였다.

### 5.2 외부 `Intent`로 업로드 작업을 생성하는 구조

`UploadService` 내부 `getTask(intent)`를 분석한 결과, 서비스는 외부 `Intent`로부터 전달된 `taskClass` 값을 읽고 reflection으로 업로드 작업 객체를 생성하고 있었다.

```java
String taskClass = intent.getStringExtra(PARAM_TASK_CLASS);
Class<?> task = Class.forName(taskClass);
uploadTask = (UploadTask) UploadTask.class.cast(task.newInstance());
uploadTask.init(this, intent);
```

이 구조는 외부 앱이 업로드 작업의 종류를 결정할 수 있다는 뜻이며, 단순히 서비스가 존재하는 수준이 아니라 **외부 입력에 따라 업로드 동작이 구성되는 구조**임을 보여준다.

### 5.3 `taskParameters`로 파일과 URL을 함께 전달받음

`UploadTask.init()`에서는 업로드 파라미터를 `Intent`에서 직접 추출하고 있었다.

```java
this.params = (UploadTaskParameters) intent.getParcelableExtra("taskParameters");
```

이후 `UploadTaskParameters`를 확인한 결과, 실제로 업로드 대상과 목적지가 아래 필드로 정의되어 있었다.

```java
private ArrayList<UploadFile> files;
private String serverUrl;
```

즉 외부에서 전달된 업로드 파라미터 안에

- 어떤 파일을 보낼지
- 어디로 보낼지

가 함께 포함되는 구조였다.

### 5.4 업로드 대상 파일은 `UploadFile.path`로 지정됨

`UploadFile`은 실제 파일 경로를 보관하는 객체였다.

```java
protected final String path;

public UploadFile(String path) throws FileNotFoundException {
    ...
    this.path = path;
}
```

즉 `files` 목록 안에는 단순 문자열이 아니라, 실제 파일 경로를 포함하는 객체가 저장된다. 이 구조상 외부 앱은 업로드 서비스에 전달할 파일 경로를 직접 구성할 수 있다.

### 5.5 `MultipartUploadTask`가 multipart body를 구성하고 파일을 읽는 구조

이번 PoC에서는 `taskClass`로 `net.gotev.uploadservice.MultipartUploadTask`를 사용하였다. 따라서 실제 재현 흐름을 설명할 때도 `MultipartUploadTask` 기준으로 보는 것이 가장 정확하다.

`MultipartUploadTask.init()`는 multipart boundary를 생성하고, `Content-Type`을 `multipart/form-data`로 설정한다.

```java
this.httpParams.addRequestHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
```

이후 `writeFiles(...)`에서는 `UploadFile`에 포함된 파일 경로를 바탕으로 실제 파일 스트림을 열고, 그 내용을 body에 기록한다.

```java
InputStream stream = file.getStream(this.service);
bodyWriter.writeStream(stream, this);
stream.close();
```

즉 `MultipartUploadTask`는 단순히 파라미터만 조립하는 것이 아니라, 업로드 body 형식을 multipart로 구성하고 실제 파일 내용을 읽어 전송하는 역할을 수행한다.

### 5.6 `HttpUploadTask`가 실제 업로드 목적지로 연결을 생성함

`MultipartUploadTask`는 `HttpUploadTask`를 상속받고 있으며, 실제 네트워크 연결은 상위 클래스인 `HttpUploadTask`에서 생성된다.

```java
UploadService.HTTP_STACK.createNewConnection(
    this.httpParams.getMethod(),
    this.params.getServerUrl()
)
```

즉 전체 흐름은 다음과 같이 정리된다.

1. 외부 앱이 `UploadService` 호출
2. `taskClass`로 업로드 작업 생성
3. `taskParameters`에서 `files`, `serverUrl` 추출
4. `MultipartUploadTask`가 multipart body와 헤더를 구성함
5. `MultipartUploadTask.writeFiles()`가 지정된 파일 스트림을 읽음
6. `HttpUploadTask`가 지정된 원격 URL로 업로드 수행

이 구조 자체가 8번 항목의 핵심 근거다.

### 5.7 왜 “파일 업로드 기능”이 아니라 “취약한 컴포넌트 사용” 문제인가

분석 과정에서 `InsecureShop` UI 상에는 사용자가 직접 사진이나 파일을 업로드하는 기능이 보이지 않았다. 그러나 이번 항목은 정상 사용자 기능을 분석하는 문제가 아니라, **앱에 포함된 취약한 third-party component가 외부에 노출되어 있는지**를 확인하는 문제다.

즉 중요한 것은 “업로드 버튼이 있느냐”가 아니라,

- 외부 앱이 호출 가능한 업로드 서비스가 존재하는지
- 그 서비스가 파일 경로와 원격 URL을 외부 입력으로 받아 처리하는지
- 결과적으로 앱 내부 파일을 외부 서버로 전송할 수 있는지

를 확인하는 것이다.

## 6. 동적 검증

### 6.1 PoC App 준비

정적 분석만으로도 위험 구조는 충분히 확인되었지만, 이번 항목에서는 실제 재현 여부를 확인하기 위해 별도 `PoC App`을 제작하였다.

PoC App에서는 다음 사항을 준비하였다.

- `android-upload-service 3.2.3` 라이브러리 의존성 추가
- cleartext HTTP 테스트를 위한 `usesCleartextTraffic="true"` 설정
- `MainActivity`에서 `UploadTaskParameters`, `HttpUploadTaskParameters`, `UploadFile`을 구성
- `Intent("net.gotev.uploadservice.action.upload")`로 `InsecureShop`의 `UploadService` 호출

이번 PoC는 `Prefs.xml`을 업로드 대상으로 지정하고, 테스트용 로컬 HTTP 수신 서버를 업로드 목적지로 사용하였다.

### 6.2 검증 대상 파일

동적 검증 대상 파일은 아래와 같았다.

```text
/data/data/com.insecureshop/shared_prefs/Prefs.xml
```

이 파일은 `InsecureShop`의 로컬 설정 파일이며, 앞선 항목에서도 `username`, `password`와 같은 민감한 값이 저장되는 파일로 확인하였다.

### 6.3 검증 결과

PoC App 실행 후 로컬 HTTP 수신 서버에는 multipart body 형태로 `Prefs.xml` 내용이 수신되었다. 수신 데이터 안에는 아래와 같이 실제 설정 값이 포함되어 있었다.

- `<string name="password">!ns3csh0p</string>`
- 제품 목록 및 기타 앱 내부 설정 데이터

또한 수신된 body는 로컬 PC에 `exfiltrated_file.bin`으로 저장되었으며, 이를 통해 `InsecureShop` 내부 파일이 외부 수신 서버로 전달되었음을 확인하였다.

즉 이번 항목은 단순히 “취약한 라이브러리를 포함하고 있다” 수준이 아니라, **해당 third-party component의 외부 노출 구조를 악용해 앱 내부 파일이 원격 도메인으로 전송될 수 있음을 직접 검증한 사례**다.

## 7. 영향도

이 구조를 악용하면 동일 기기에 설치된 악성 앱이 `InsecureShop`의 `UploadService`를 직접 호출해 앱 내부 파일을 임의의 외부 서버로 전송할 수 있다. 실제 서비스 환경에서 이와 같은 구조가 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- SharedPreferences XML 유출
- 앱 내부 설정 파일 및 세션 관련 데이터 유출
- 평문 자격증명, 사용자 정보, 기타 민감 데이터 유출
- 사용자가 인지하지 못한 상태에서 백그라운드 파일 전송 발생

즉 이번 문제는 단순 라이브러리 포함 여부에 그치지 않고, **취약한 third-party component가 실제 데이터 유출 경로로 악용될 수 있다는 점**에서 위험하다.

## 8. 대응 방안

- 취약한 `android-upload-service` 버전을 제거하거나 최신 안전 버전으로 업데이트해야 한다.
- `UploadService`를 외부에 노출하지 않도록 `exported=false`로 제한해야 한다.
- 업로드 서비스 호출 시 서명 검증, 권한 검증, 호출자 검증 로직을 추가해야 한다.
- 외부 `Intent`를 통해 파일 경로와 원격 URL을 직접 받지 않도록 구조를 수정해야 한다.
- 앱 내부 파일을 업로드 대상으로 직접 지정할 수 없도록 경로 검증과 allowlist 정책을 적용해야 한다.

## 9. 결론

이번 분석에서는 `InsecureShop`에 포함된 `net.gotev.uploadservice.UploadService`가 `exported=true` 상태로 외부에 노출되어 있으며, 외부 `Intent`를 통해 업로드 대상 파일과 원격 URL을 함께 받아 실제 전송까지 수행하는 구조임을 확인하였다.

추가로 별도 `PoC App`과 로컬 HTTP 수신 서버를 이용한 검증 결과, 앱 내부 `Prefs.xml` 파일이 외부 서버로 전달되는 것을 확인하였다. 이를 통해 `Using Components with Known Vulnerabilities` 항목은 단순 참고 수준이 아니라, **취약한 third-party component 사용이 실제 로컬 파일 유출로 이어질 수 있음을 재현한 finding**으로 정리할 수 있었다.

## 10. 취약점 테스트

### 1. Manifest에서 외부 노출된 UploadService 확인

![1. Manifest에서 외부 노출된 UploadService 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/01-uploadservice-manifest.png)

`net.gotev.uploadservice.UploadService`가 `enabled=true`, `exported=true` 상태로 선언되어 있다. 이는 앱 내부에 외부 앱이 직접 호출할 수 있는 third-party upload service가 존재한다는 뜻이다.

### 2. 외부 Intent로 업로드 task를 생성하는 getTask() 확인

![2. 외부 Intent로 업로드 task를 생성하는 getTask() 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/02-uploadservice-gettask.png)

`getTask(intent)`는 `taskClass` 값을 읽어 reflection으로 업로드 작업 객체를 생성하고 `init(this, intent)`를 호출한다. 즉 업로드 동작의 종류가 외부 `Intent`에 의해 결정된다.

### 3. taskParameters를 Intent에서 직접 추출하는 UploadTask.init() 확인

![3. taskParameters를 Intent에서 직접 추출하는 UploadTask.init() 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/03-uploadtask-init-taskparameters.png)

`UploadTask.init()`는 `taskParameters`를 그대로 `Intent`에서 꺼낸다. 이 지점에서 외부에서 전달된 업로드 설정이 런타임 객체로 들어간다.

### 4. taskParameters 내부에 files와 serverUrl이 존재함을 확인

![4. taskParameters 내부에 files와 serverUrl이 존재함을 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/04-uploadtaskparameters-fields.png)

`UploadTaskParameters`에는 업로드 대상 파일 목록(`files`)과 업로드 목적지(`serverUrl`)가 포함되어 있다. 즉 어떤 파일을 어디로 보낼지가 외부 입력으로 제어되는 구조다.

### 5. UploadFile이 실제 파일 경로(path)를 보관함을 확인

![5. UploadFile이 실제 파일 경로(path)를 보관함을 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/05-uploadfile-path.png)

`UploadFile`은 실제 파일 경로를 저장하는 객체다. 따라서 업로드 서비스는 외부에서 지정된 로컬 파일 경로를 그대로 처리할 수 있다.

### 6. MultipartUploadTask가 multipart/form-data 헤더를 구성하는 코드 확인

![6. MultipartUploadTask가 multipart/form-data 헤더를 구성하는 코드 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/06-multipartuploadtask-init-content-type.png)

`MultipartUploadTask.init()`는 boundary를 생성하고 `Content-Type: multipart/form-data; boundary=...` 헤더를 추가한다. 서버에서 확인된 multipart body가 왜 생성되었는지 설명해주는 핵심 근거다.

### 7. MultipartUploadTask가 파일 스트림을 실제로 읽어 body에 쓰는 코드 확인

![7. MultipartUploadTask가 파일 스트림을 실제로 읽어 body에 쓰는 코드 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/07-multipartuploadtask-writefiles.png)

`writeFiles(...)`는 `file.getStream(this.service)`로 지정된 파일을 열고, `bodyWriter.writeStream(...)`으로 그 내용을 multipart body에 기록한다. 이 코드는 로컬 파일이 실제 업로드 body에 포함된다는 직접 근거다.

### 8. HttpUploadTask가 serverUrl로 실제 HTTP 연결을 만드는 코드 확인

![8. HttpUploadTask가 serverUrl로 실제 HTTP 연결을 만드는 코드 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/08-httpuploadtask-create-connection.png)

`HttpUploadTask`는 `this.params.getServerUrl()` 값을 사용해 실제 HTTP 연결을 생성한다. 즉 업로드 목적지는 코드에 고정된 것이 아니라 외부 파라미터에 의해 결정된다.

### 9. PoC App에 취약 라이브러리 저장소를 추가한 모습

![9. PoC App에 취약 라이브러리 저장소를 추가한 모습](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/09-poc-jitpack-repository.png)

PoC App에서는 취약한 라이브러리 버전을 가져오기 위해 `jitpack.io` 저장소를 추가하였다.

### 10. PoC App에 취약한 android-upload-service 3.2.3 의존성을 추가한 모습

![10. PoC App에 취약한 android-upload-service 3.2.3 의존성을 추가한 모습](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/10-poc-vulnerable-dependency.png)

PoC App은 `com.github.gotev.android-upload-service:uploadservice:3.2.3` 의존성을 포함해, `InsecureShop`에 포함된 취약 컴포넌트 구조를 그대로 재현하도록 구성하였다.

### 11. PoC App Manifest 설정 확인

![11. PoC App Manifest 설정 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/11-poc-manifest.png)

PoC App에는 `INTERNET` 권한과 `usesCleartextTraffic="true"`가 적용되어 있으며, 실행용 `MainActivity`가 정의되어 있다. 이는 테스트용 업로드 요청을 전송하기 위한 최소 설정이다.

### 12. PoC App이 InsecureShop의 UploadService를 호출하도록 구성한 코드 확인

![12. PoC App이 InsecureShop의 UploadService를 호출하도록 구성한 코드 확인](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/12-poc-mainactivity.png)

PoC App은 `UploadTaskParameters`, `HttpUploadTaskParameters`, `UploadFile`을 구성한 뒤 `Intent("net.gotev.uploadservice.action.upload")`로 `InsecureShop`의 `UploadService`를 직접 호출하도록 만들었다. 이 과정에서 `taskClass`는 `net.gotev.uploadservice.MultipartUploadTask`로 설정되었고, 대상 파일은 `Prefs.xml`, 목적지는 테스트용 로컬 수신 서버로 지정하였다.

### 13. 로컬 수신 서버에서 Prefs.xml 내용이 실제로 전달된 모습

![13. 로컬 수신 서버에서 Prefs.xml 내용이 실제로 전달된 모습](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/13-receiver-prefs-content.png)

로컬 HTTP 수신 서버에는 multipart body 형태로 `Prefs.xml` 내용이 전달되었고, 그 안에서 `password`, 제품 목록 등 앱 내부 설정 값이 실제로 확인되었다. 이 결과는 실제 PoC가 `MultipartUploadTask` 경로를 통해 동작했음을 뒷받침한다.

### 14. 수신 body가 로컬 파일로 저장된 모습

![14. 수신 body가 로컬 파일로 저장된 모습](../images/08-Using%20Components%20with%20Known%20Vulnerabilities/14-exfiltrated-file-bin.png)

수신된 요청 body는 로컬 PC에 `exfiltrated_file.bin`으로 저장되었다. 이는 `InsecureShop` 내부 파일이 외부 수신 환경으로 전송되었음을 보여주는 최종 증적이다.
