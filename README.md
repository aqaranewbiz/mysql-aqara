# MySQL MCP 서버
[![smithery badge](https://smithery.ai/badge/@aqaranewbiz/mysql-aqaranewbiz)](https://smithery.ai/server/@aqaranewbiz/mysql-aqaranewbiz)
이 프로젝트는 Smithery의 Model Context Protocol (MCP)을 사용하여 MySQL 데이터베이스와 상호작용하는 서버입니다.

## Installation

### Installing via Smithery
To install MySQL Server for Claude Desktop automatically via Smithery:

```bash
npx -y @smithery/cli install @aqaranewbiz/mysql-aqaranewbiz --client claude
```

### Manual Installation
```bash
npx @aqaranewbiz/mysql-aqaranewbiz
```

## Configuration

The server requires database connection information to be provided when connecting. You can configure this in your MCP settings:

```json
{
  "mcpServers": {
    "mysql": {
      "command": "npx",
      "args": ["-y", "@aqaranewbiz/mysql-aqaranewbiz"]
    }
  }
}
```

## Available Tools

### 1. connect_db
Establish connection to MySQL database using provided credentials.

```javascript
use_mcp_tool({
  server_name: "mysql",
  tool_name: "connect_db",
  arguments: {
    host: "localhost",
    user: "your_user",
    password: "your_password",
    database: "your_database"
  }
});
```

### 2. query
Execute SELECT queries with optional prepared statement parameters.

```javascript
use_mcp_tool({
  server_name: "mysql",
  tool_name: "query",
  arguments: {
    sql: "SELECT * FROM users WHERE id = ?",
    params: [1]
  }
});
```

### 3. execute
Execute INSERT, UPDATE, or DELETE queries with optional prepared statement parameters.

```javascript
use_mcp_tool({
  server_name: "mysql",
  tool_name: "execute",
  arguments: {
    sql: "INSERT INTO users (name, email) VALUES (?, ?)",
    params: ["John Doe", "john@example.com"]
  }
});
```

### 4. list_tables
List all tables in the connected database.

```javascript
use_mcp_tool({
  server_name: "mysql",
  tool_name: "list_tables",
  arguments: {}
});
```

### 5. describe_table
Get the structure of a specific table.

```javascript
use_mcp_tool({
  server_name: "mysql",
  tool_name: "describe_table",
  arguments: {
    table: "users"
  }
});
```

## 주요 기능

- MySQL 데이터베이스 연결 및 쿼리 실행
- MCP 프로토콜을 통한 표준화된 API 제공
- 직접 입력 방식의 데이터베이스 연결 설정

## 시작하기

### 필수 요구사항

- Python 3.11 이상
- MySQL 서버
- Docker (선택사항)

### 설치 방법

#### 로컬 설치 (권장)

1. Python 가상환경 생성 및 활성화:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

3. 서버 실행:
```bash
python mcp_server.py
```

#### Docker 설치

1. Docker 이미지 빌드:
```bash
docker build -t mysql-mcp-server .
```

2. 컨테이너 실행:
```bash
docker run mysql-mcp-server
```

### 로컬 개발 설정

1. 개발 환경 설정:
```bash
# 개발용 의존성 설치
pip install -r requirements-dev.txt  # 필요한 경우 생성

# 코드 포맷팅 및 린팅 설정
pip install black flake8
```

2. 코드 실행:
```bash
# 개발 모드로 실행
python mcp_server.py --dev
```

3. 테스트 실행:
```bash
# 테스트 실행
python -m pytest tests/
```

## API 엔드포인트

### 서버 정보 조회
```
GET /status
```
서버의 상태와 사용 가능한 도구 목록을 반환합니다.

### 쿼리 실행
```
POST /execute
```
MySQL 쿼리를 실행하고 결과를 반환합니다.

## 개발 가이드

### 프로젝트 구조
```
@MCP-Server-for-Smithery/
├── mcp_server.py      # 메인 서버 코드
├── requirements.txt   # Python 의존성
├── Dockerfile        # Docker 설정
└── tests/            # 테스트 코드
```

### 새로운 기능 추가

1. `mcp_server.py`에 새로운 도구 추가
2. 필요한 의존성 `requirements.txt`에 추가
3. 테스트 코드 작성
4. Docker 이미지 재빌드 (Docker 사용 시)

## 문제 해결

### 일반적인 문제

1. 연결 오류:
   - MySQL 서버가 실행 중인지 확인
   - 연결 정보가 올바르게 입력되었는지 확인
   - 로컬 설치 시 MySQL 클라이언트 라이브러리가 설치되어 있는지 확인

2. 쿼리 실행 오류:
   - SQL 구문 검사
   - 데이터베이스 권한 확인
   - 로컬 설치 시 MySQL 커넥터 버전 확인

### 로깅

서버는 기본적으로 로그를 표준 출력에 기록합니다. 로컬 설치 시 로그 레벨을 조정하려면:
```bash
python mcp_server.py --log-level DEBUG
```

Docker를 사용하는 경우 로그를 확인하려면:
```bash
docker logs [container-id]
```

## 기여하기

1. 이슈 생성
2. 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치 푸시 (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 연락처

문의사항이 있으시면 이슈를 생성해주세요. 