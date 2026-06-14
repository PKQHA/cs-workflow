# Agents Guide

## 项目概览

这是一个酒店客服自动化系统演示项目，包含 FastAPI 后端和 Streamlit 前端。

核心目标：

- 帮助客服处理客户咨询、订房推荐、表单管理、房态维护、Excel 上传和投诉处理。
- 后端负责业务规则、Excel 持久化、AI 网关、会话上下文和 API。
- 前端负责页面展示、用户输入、错误提示和调用后端 API。

## 主要目录

- `backend/`：FastAPI 后端。
- `backend/app/api/`：HTTP API 路由。
- `backend/app/services/`：业务服务和 AI 网关。
- `backend/app/rules/`：确定性业务规则。
- `backend/app/repositories/`：Excel 仓储。
- `backend/app/schemas/`：Pydantic 数据结构和请求体。
- `backend/tests/`：后端测试。
- `frontend/`：Streamlit 前端。
- `frontend/services/api_client.py`：前端 API Client，读取 `BACKEND_BASE_URL`。
- `frontend/pages/`：前端页面。
- `frontend/components/`：前端展示组件。
- `tasks/`：模块任务和进度记录。
- `shared/`：共享示例资源。

## 本地运行

后端：

```powershell
$env:PYTHONPATH="C:\Users\L1529\Desktop\ai-study\workbench\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 7860
```

前端：

```powershell
$env:BACKEND_BASE_URL="http://127.0.0.1:7860"
.\.venv\Scripts\python.exe -m streamlit run frontend\app.py --server.address 127.0.0.1 --server.port 8501
```

测试：

```powershell
$env:PYTHONPATH="C:\Users\L1529\Desktop\ai-study\workbench\backend"
.\.venv\Scripts\pytest.exe backend\tests -q
```

## 开发规则

- 不要提交 `.env`、真实 Excel、真实客户数据、日志、缓存或虚拟环境。
- 不要把 API Key 写进代码、README、任务文档或测试文件。
- 后端 API 返回结构已经被前端依赖，修改前必须同步更新前端和测试。
- Excel 写入失败必须返回明确中文错误，不允许只提示“保存失败”。
- 推荐逻辑必须只使用空房，不允许推荐已住或已预订房间。
- 前端必须通过 `BACKEND_BASE_URL` 读取后端地址，不允许写死部署地址。
- 每次改动后优先运行相关测试；涉及后端时运行 `pytest backend/tests -q`。
- 修改 `tasks/` 中对应 checklist 和 `tasks/progress.md`，保持真实状态。

## Git 提交流程

每次执行完操作后都要上传到 Git。

标准流程：

```powershell
git status
git add .
git status
git commit -m "描述本次修改"
git push
```

提交前必须确认：

```powershell
git check-ignore .env
git status --short
```

如果 `git status --short` 中出现 `.env`、`.venv/`、`*.xlsx`、`*.xls`、`__pycache__/` 或 `.pytest_cache/`，必须先修正 `.gitignore` 或取消暂存，不能提交。

## 当前远程仓库

GitHub 仓库：

```text
https://github.com/PKQHA/cs-workflow.git
```
