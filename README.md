# 酒店客服自动化系统

这是一个演示版酒店客服工作台，目标是支持订房推荐、表单管理、房态维护、Excel 持久化、知识问答和投诉处理。

## 当前技术栈

- 后端：Python + FastAPI
- 数据校验：Pydantic
- Excel：openpyxl
- 前端规划：Streamlit Community Cloud
- 后端部署规划：Hugging Face Docker Space

## 本地后端运行

1. 进入项目根目录。
2. 安装依赖：`pip install -r backend/requirements.txt`
3. 启动后端：`uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 7860`
4. 健康检查：访问 `http://localhost:7860/health`

## 本地前端运行

1. 安装前端依赖：`pip install -r frontend/requirements.txt`
2. 设置后端地址环境变量：`$env:BACKEND_BASE_URL="http://127.0.0.1:7860"`
3. 启动 Streamlit：`streamlit run frontend/app.py --server.port 8501`
4. 浏览器访问：`http://127.0.0.1:8501`

前端不会读取或保存 API Key，只通过 `BACKEND_BASE_URL` 调用后端。

## 环境变量

复制 `.env.example` 为 `.env` 后按需修改。真实 API Key 只能放在本地 `.env`、Streamlit Secret 或 Hugging Face Space Secret 中，不能写入代码或文档。

## Docker

本地构建并启动后端：

```powershell
docker compose up --build backend
```

## 测试

当前核心模块可用标准库测试运行：

```powershell
python -m unittest discover backend/tests
```

如果使用项目依赖环境，也可以后续接入 `pytest`。
