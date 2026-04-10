# InsecureShop - AWS Cognito Misconfiguration

## 1. 개요

`InsecureShop`를 분석하던 중 앱 리소스 내부에 AWS Cognito Identity Pool ID가 하드코딩되어 있는 것을 확인하였다. 이후 해당 Identity Pool ID를 이용해 AWS Cognito Identity API를 호출한 결과, 비인증 사용자에 대한 `IdentityId`와 임시 AWS 자격증명을 발급받을 수 있었다.

발급된 임시 자격증명으로 S3 접근 권한을 확인한 결과, 버킷 목록 조회와 특정 버킷 내부 객체 목록 조회가 가능했고, `geolocation-pocfiles` 버킷의 `geo.html` 객체를 다운로드하여 로컬에서 내용을 확인할 수 있었다.

코드 흐름을 순서대로 보면 다음과 같다.

1. 디컴파일된 앱 리소스에서 `aws_Identity_pool_ID` 확인
2. `nuclei`의 `aws-cognito` file template로 Cognito Pool ID 패턴 탐지
3. AWS CLI로 `get-id`를 호출해 `IdentityId` 발급
4. `get-credentials-for-identity`를 호출해 임시 AWS 자격증명 발급
5. 임시 자격증명으로 `sts get-caller-identity` 및 `s3 ls` 수행
6. 접근 가능한 S3 버킷과 객체 목록 확인
7. `s3api get-object`로 S3 객체 다운로드 및 내용 확인

즉 앱에 포함된 Cognito Identity Pool 설정이 비인증 임시 자격증명 발급과 과도한 S3 접근 권한으로 이어지는 구조였다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `AWS Cognito Misconfiguration` |
| 취약점 유형 | 하드코딩된 Cognito Identity Pool ID 및 과도한 unauth role 권한 |
| 영향 | 비인증 임시 AWS 자격증명 발급, S3 버킷 및 객체 열람 가능 |
| 분석 도구 | `APK Easy Tool`, `nuclei`, `jadx`, `AWS CLI`, `PowerShell` |
| 핵심 값 | `aws_Identity_pool_ID` |
| 검증된 접근 | `s3.list_buckets`, `s3api get-object` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 디컴파일 도구 | `APK Easy Tool` |
| 정적 탐지 | `nuclei v3.7.1`, `aws-cognito.yaml` |
| 정적 확인 | `jadx`, `resources.arsc:/res/values/strings.xml` |
| 후속 검증 | `AWS CLI`, `PowerShell` |
| AWS 리전 | `us-east-1` |

## 4. 분석 방법

이번 항목은 “앱에 포함된 Cognito Identity Pool ID가 실제 AWS 리소스 접근으로 이어지는지”를 기준으로 다음 순서로 분석하였다.

1. `APK Easy Tool`로 APK를 디컴파일해 리소스 파일을 확인하였다.
2. `nuclei`의 `aws-cognito.yaml` file template로 디컴파일 결과물에서 Cognito Pool ID 패턴을 탐지하였다.
3. `strings.xml`과 `R.string` 리소스에서 `aws_Identity_pool_ID`가 실제로 존재하는지 확인하였다.
4. AWS CLI로 `get-id`를 호출하여 `IdentityId` 발급 가능 여부를 확인하였다.
5. 발급된 `IdentityId`로 `get-credentials-for-identity`를 호출하여 임시 자격증명 발급 가능 여부를 확인하였다.
6. 발급된 임시 자격증명을 현재 PowerShell 세션의 환경변수로 설정한 뒤, `sts`와 `s3` 명령으로 권한을 확인하였다.
7. 접근 가능한 버킷 내부 객체를 나열하고, `geo.html` 객체를 다운로드해 파일 접근 가능성을 검증하였다.

## 5. 상세 분석

### 5.1 `nuclei` Cognito 탐지 템플릿 확인

`nuclei-templates` 안에서 AWS Cognito Pool ID를 탐지하는 file template를 확인하였다.

![aws-cognito.yaml 템플릿 위치 확인](../images/10-AWS%20Cognito%20Misconfiguration/05-aws-cognito-template-path.png)

해당 템플릿은 `file/keys/amazon/aws-cognito.yaml` 위치에 있으며, Cognito Identity Pool ID 형식의 문자열을 정규식으로 탐지한다.

### 5.2 APK 디컴파일 결과물 준비

`APK Easy Tool`을 사용해 `InsecureShop.apk`를 디컴파일하였다.

![APK Easy Tool 디컴파일 성공](../images/10-AWS%20Cognito%20Misconfiguration/03-apk-easy-tool-decompile-success.png)

디컴파일 결과 폴더에는 `AndroidManifest.xml`, `res`, `smali` 등 정적 분석에 필요한 파일들이 생성되었다.

![디컴파일 결과 폴더 확인](../images/10-AWS%20Cognito%20Misconfiguration/04-apk-easy-tool-decompiled-folder.png)

### 5.3 `nuclei`로 Cognito Identity Pool ID 탐지

디컴파일된 폴더를 대상으로 `aws-cognito.yaml` file template를 실행하였다.

```powershell
.\nuclei.exe -file -t "C:\Users\user\nuclei-templates\file\keys\amazon\aws-cognito.yaml" -target "C:\Users\user\Documents\APK Easy Tool\1-Decompiled APKs\InsecureShop"
```

실행 결과 `res\values\strings.xml`에서 Cognito Identity Pool ID 형식의 문자열이 탐지되었다.

![nuclei로 Cognito Identity Pool ID 탐지](../images/10-AWS%20Cognito%20Misconfiguration/06-nuclei-cognito-pool-detection.png)

탐지된 값은 다음과 같았다.

```text
us-east-1:7e9426f7-42af-4717-8689-00a9a4b65c1c
```

### 5.4 `strings.xml`에서 `aws_Identity_pool_ID` 확인

탐지 결과를 바탕으로 리소스 파일을 직접 확인한 결과, `strings.xml`에 아래 문자열이 존재하였다.

```xml
<string name="aws_Identity_pool_ID">us-east-1:7e9426f7-42af-4717-8689-00a9a4b65c1c</string>
```

![strings.xml의 aws_Identity_pool_ID 확인](../images/10-AWS%20Cognito%20Misconfiguration/07-strings-xml-identity-pool-id.png)

또한 `R.string` 리소스에도 `aws_Identity_pool_ID`가 등록되어 있었다.

![R.string에 aws_Identity_pool_ID 등록 확인](../images/10-AWS%20Cognito%20Misconfiguration/08-r-string-identity-pool-resource.png)

이 단계에서 앱 리소스 내부에 Cognito Identity Pool ID가 하드코딩되어 있다는 점을 확인하였다.

### 5.5 AWS CLI로 `IdentityId` 발급 확인

AWS CLI 설치 후 버전을 확인하였다.

![AWS CLI 버전 확인](../images/10-AWS%20Cognito%20Misconfiguration/09-aws-cli-version.png)

이후 앱에서 확인한 Identity Pool ID를 사용해 `get-id`를 호출하였다.

```powershell
aws cognito-identity get-id --identity-pool-id "us-east-1:7e9426f7-42af-4717-8689-00a9a4b65c1c" --region us-east-1
```

호출 결과 `IdentityId`가 발급되었다.

![get-id로 IdentityId 발급 확인](../images/10-AWS%20Cognito%20Misconfiguration/10-cognito-get-id-identityid.png)

이 결과는 하드코딩된 Identity Pool ID를 통해 비인증 Identity 발급이 가능함을 보여준다.

### 5.6 임시 AWS 자격증명 발급 및 역할 확인

발급된 `IdentityId`를 사용해 `get-credentials-for-identity`를 호출하면 `AccessKeyId`, `SecretKey`, `SessionToken`, `Expiration`이 포함된 임시 AWS 자격증명을 받을 수 있었다.

```powershell
aws cognito-identity get-credentials-for-identity --identity-id "us-east-1:15f0125a-1fe0-c95b-9d6d-4b5bf9f96c68" --region us-east-1
```

임시 자격증명 원본 출력에는 실제 키와 세션 토큰이 포함되므로 본문 증적에는 직접 포함하지 않았다. 대신 발급된 임시 자격증명을 PowerShell 환경변수로 설정한 뒤 `sts get-caller-identity`를 실행하여 해당 자격증명이 어떤 역할로 동작하는지 확인하였다.

![get-credentials-for-identity로 임시 자격증명 발급 확인](../images/10-AWS%20Cognito%20Misconfiguration/11-get-credentials-redacted.png)

![PowerShell 환경변수로 임시 자격증명 설정](../images/10-AWS%20Cognito%20Misconfiguration/12-powershell-env-vars-redacted.png)

![sts get-caller-identity로 Cognito unauth role 확인](../images/10-AWS%20Cognito%20Misconfiguration/13-sts-caller-identity-unauth-role.png)

응답에서 다음 role 경로가 확인되었다.

```text
arn:aws:sts::094222047775:assumed-role/Cognito_InsecureshopUnauth_Role/CognitoIdentityCredentials
```

즉 발급된 임시 자격증명은 `Cognito_InsecureshopUnauth_Role`로 동작하고 있었다.

### 5.7 S3 버킷 목록 조회

임시 자격증명을 사용한 상태에서 `aws s3 ls`를 실행하자 S3 버킷 목록이 조회되었다.

![aws s3 ls로 버킷 목록 조회](../images/10-AWS%20Cognito%20Misconfiguration/14-s3-bucket-list.png)

확인된 버킷은 다음과 같았다.

```text
elasticbeanstalk-us-west-2-094222047733
elasticbeanstalk-us-west-2-094222047775
geolocation-pocfiles
```

이 결과는 unauth role에 최소한 S3 버킷 목록 조회 권한이 존재함을 보여준다.

### 5.8 버킷 내부 객체 목록 확인

첫 번째 버킷은 비어 있었지만, 다른 버킷에서는 내부 객체 목록을 확인할 수 있었다.

![빈 버킷 조회 결과](../images/10-AWS%20Cognito%20Misconfiguration/15-empty-elasticbeanstalk-bucket.png)

`elasticbeanstalk-us-west-2-094222047775` 버킷에서는 여러 텍스트 객체가 조회되었다.

![elasticbeanstalk 버킷 객체 목록 확인](../images/10-AWS%20Cognito%20Misconfiguration/16-elasticbeanstalk-bucket-objects.png)

`geolocation-pocfiles` 버킷에서도 `geo.html` 등 여러 객체가 조회되었다.

![geolocation-pocfiles 버킷 객체 목록 확인](../images/10-AWS%20Cognito%20Misconfiguration/17-geolocation-pocfiles-objects.png)

이 단계에서 단순 버킷 이름뿐 아니라 버킷 내부 객체 목록까지 열람 가능함을 확인하였다.

### 5.9 S3 객체 다운로드 및 내용 확인

마지막으로 `geolocation-pocfiles` 버킷의 `geo.html` 객체를 다운로드하였다.

```powershell
aws s3api get-object --bucket geolocation-pocfiles --key geo.html geo.html
```

![s3api get-object로 geo.html 다운로드](../images/10-AWS%20Cognito%20Misconfiguration/18-s3-get-object-geo-html.png)

다운로드 후 `Get-Content`로 파일 내용을 확인하였다.

![geo.html 내용 확인](../images/10-AWS%20Cognito%20Misconfiguration/19-geo-html-content.png)

이를 통해 발급받은 Cognito 임시 자격증명이 단순 목록 조회뿐 아니라 실제 S3 객체 읽기 권한까지 가지고 있음을 검증하였다.

## 6. 영향

이 구성에서는 앱에 포함된 Identity Pool ID만으로 비인증 Identity와 임시 AWS 자격증명을 발급받을 수 있었다. 또한 해당 자격증명은 `Cognito_InsecureshopUnauth_Role`로 동작하며, S3 버킷 목록과 일부 버킷 내부 객체를 조회할 수 있었다.

실제 서비스 환경에서 동일한 구성이 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- 비인증 사용자가 클라우드 임시 자격증명을 발급받을 수 있음
- S3 버킷 이름과 내부 객체 목록이 노출될 수 있음
- S3 객체 다운로드를 통해 파일 내용이 노출될 수 있음
- unauth role에 쓰기 권한까지 포함된 경우 객체 변조 또는 업로드로 이어질 수 있음

이번 검증에서는 읽기 및 목록 조회 중심으로 확인했으며, 불필요한 객체 업로드나 수정 테스트는 수행하지 않았다.

## 7. 대응 방안

- Cognito Identity Pool의 unauthenticated identity 사용 여부를 재검토해야 한다.
- unauth role에 부여된 IAM 정책을 최소 권한 원칙에 맞게 제한해야 한다.
- 비인증 사용자에게 `s3:ListAllMyBuckets`, `s3:ListBucket`, `s3:GetObject` 등 과도한 권한을 부여하지 않아야 한다.
- 앱 리소스에 클라우드 식별자가 포함되는 경우, 해당 값 자체를 비밀값으로 간주하기보다 연결된 IAM role 권한을 안전하게 구성해야 한다.
- S3 버킷 정책과 IAM role 정책을 함께 점검해 불필요한 public/unauthenticated access를 제거해야 한다.
- 클라우드 리소스 접근이 필요한 경우 서버 측에서 권한을 중개하거나, 인증된 사용자에 한해 제한된 범위의 임시 권한만 발급해야 한다.

## 8. 정리

이번 분석에서는 `InsecureShop` 리소스 내부에 `aws_Identity_pool_ID`라는 이름으로 AWS Cognito Identity Pool ID가 하드코딩되어 있음을 확인하였다. `nuclei`의 `aws-cognito` file template로 해당 값을 탐지하고, `strings.xml`과 `R.string` 리소스에서 직접 재확인하였다.

이후 AWS CLI를 사용해 해당 Identity Pool ID로 `IdentityId`와 임시 AWS 자격증명을 발급받았고, 발급된 자격증명이 `Cognito_InsecureshopUnauth_Role`로 동작함을 확인하였다. 최종적으로 `aws s3 ls`와 `aws s3api get-object`를 통해 S3 버킷 목록, 버킷 내부 객체 목록, 특정 객체 다운로드까지 검증하였다.

따라서 10번 항목은 **잘못 구성된 AWS Cognito unauth role을 통해 S3 리소스에 접근할 수 있는 `AWS Cognito Misconfiguration` 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

### 1. aws-cognito.yaml 템플릿 위치 확인

![1. aws-cognito.yaml 템플릿 위치 확인](../images/10-AWS%20Cognito%20Misconfiguration/05-aws-cognito-template-path.png)

`file/keys/amazon/aws-cognito.yaml` 템플릿을 사용해 Cognito Identity Pool ID 패턴을 탐지할 수 있었다.

### 2. APK Easy Tool로 InsecureShop 디컴파일

![2. APK Easy Tool 디컴파일 성공](../images/10-AWS%20Cognito%20Misconfiguration/03-apk-easy-tool-decompile-success.png)

`InsecureShop.apk`를 디컴파일하여 `res`, `smali`, `AndroidManifest.xml` 등 정적 분석 가능한 파일 구조를 확보하였다.

### 3. nuclei로 Cognito Pool ID 탐지

![3. nuclei로 Cognito Identity Pool ID 탐지](../images/10-AWS%20Cognito%20Misconfiguration/06-nuclei-cognito-pool-detection.png)

`res\values\strings.xml`에서 Cognito Identity Pool ID 형식의 문자열이 탐지되었다.

### 4. strings.xml에서 aws_Identity_pool_ID 확인

![4. strings.xml의 aws_Identity_pool_ID 확인](../images/10-AWS%20Cognito%20Misconfiguration/07-strings-xml-identity-pool-id.png)

`aws_Identity_pool_ID` 리소스 값으로 `us-east-1:7e9426f7-42af-4717-8689-00a9a4b65c1c`가 포함되어 있었다.

### 5. R.string 리소스 등록 확인

![5. R.string에 aws_Identity_pool_ID 등록 확인](../images/10-AWS%20Cognito%20Misconfiguration/08-r-string-identity-pool-resource.png)

`aws_Identity_pool_ID`가 `R.string` 리소스로도 등록되어 있어 앱 코드에서 참조 가능한 리소스임을 확인하였다.

### 6. Cognito get-id 호출로 IdentityId 발급

![6. get-id로 IdentityId 발급 확인](../images/10-AWS%20Cognito%20Misconfiguration/10-cognito-get-id-identityid.png)

하드코딩된 Identity Pool ID를 이용해 `IdentityId`를 발급받을 수 있었다.

### 7. 임시 자격증명의 STS 역할 확인

![7. get-credentials-for-identity로 임시 자격증명 발급 확인](../images/10-AWS%20Cognito%20Misconfiguration/11-get-credentials-redacted.png)

`get-credentials-for-identity` 호출 결과 `AccessKeyId`, `SecretKey`, `SessionToken`이 발급되었다. 원본 자격증명 값은 민감정보이므로 증적 이미지에서는 마스킹하였다.

![8. PowerShell 환경변수로 임시 자격증명 설정](../images/10-AWS%20Cognito%20Misconfiguration/12-powershell-env-vars-redacted.png)

발급된 임시 자격증명은 현재 PowerShell 세션의 환경변수로 설정한 뒤 후속 AWS CLI 명령에 사용하였다.

![9. sts get-caller-identity로 Cognito unauth role 확인](../images/10-AWS%20Cognito%20Misconfiguration/13-sts-caller-identity-unauth-role.png)

발급받은 임시 자격증명은 `Cognito_InsecureshopUnauth_Role`로 동작하였다.

### 8. S3 버킷 목록 조회

![8. aws s3 ls로 버킷 목록 조회](../images/10-AWS%20Cognito%20Misconfiguration/14-s3-bucket-list.png)

임시 자격증명으로 `aws s3 ls`를 실행한 결과 여러 S3 버킷 목록이 조회되었다.

### 9. 버킷 내부 객체 목록 조회

![9. elasticbeanstalk 버킷 객체 목록 확인](../images/10-AWS%20Cognito%20Misconfiguration/16-elasticbeanstalk-bucket-objects.png)

![10. geolocation-pocfiles 버킷 객체 목록 확인](../images/10-AWS%20Cognito%20Misconfiguration/17-geolocation-pocfiles-objects.png)

두 버킷에서 내부 객체 목록을 확인할 수 있었다.

### 10. S3 객체 다운로드 및 내용 확인

![11. s3api get-object로 geo.html 다운로드](../images/10-AWS%20Cognito%20Misconfiguration/18-s3-get-object-geo-html.png)

![12. geo.html 내용 확인](../images/10-AWS%20Cognito%20Misconfiguration/19-geo-html-content.png)

`geolocation-pocfiles` 버킷의 `geo.html` 객체를 다운로드하고 로컬에서 내용을 확인하였다. 이를 통해 S3 객체 읽기 권한까지 검증하였다.
