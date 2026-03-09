# Roseate-WMS

Roseate-WMS（蕴香和本轻量化仓库管理系统）面向美妆、医药等强批次管理场景，核心目标是围绕批次（Batch）和 FIFO 出库构建轻量、可扩展、移动优先的仓储系统。

## 当前完成范围

### Stage 1
- JWT 登录与受保护接口
- Vue 3 + Vite + Tailwind 基础框架
- 全局路由守卫与 Axios Token 注入
- 桌面侧边栏 / 移动端底部导航响应式布局

### Stage 2
- `Product` / `Batch` 批次化库存模型
- 商品中心：商品建档、模糊搜索、总库存聚合展示
- H5 入库流程：识别条码/内部编码、缺档引导、批次入库
- 入库合并逻辑：同一商品 + 相同到期日累加到同一批次

## 目录结构
```text
roseate-wms/
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── extensions.py
│   ├── models.py
│   ├── requirements.txt
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       └── test_inventory.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── src/
│       ├── App.vue
│       ├── api/http.js
│       ├── layouts/MainLayout.vue
│       ├── main.js
│       ├── router/index.js
│       ├── style.css
│       └── views/
│           ├── HomeView.vue
│           ├── InboundView.vue
│           ├── LoginView.vue
│           ├── OutboundView.vue
│           ├── ProductsView.vue
│           └── StockView.vue
├── tasks/
│   ├── devlog.md
│   ├── lessons.md
│   └── todo.md
└── README.md
```

## 后端模型

### `User`
- 字段：`id`, `username`, `password_hash`, `role`, `extra_data`

### `Product`
- 字段：`hb_code`, `barcode`, `name`, `spec`, `unit`, `extra_data`
- `hb_code` 为内部唯一编码主键
- 商品总库存不落库，始终由关联批次中 `current_quantity > 0` 的记录动态汇总

### `Batch`
- 字段：`id`, `hb_code`, `batch_no`, `production_date`, `expiry_date`, `cost`, `initial_quantity`, `current_quantity`, `extra_data`
- 入库合并键：`hb_code + expiry_date`
- `expiry_date` 是 FIFO 和批次排序的核心字段

## API

所有响应统一为：

```json
{
  "code": 200,
  "data": {},
  "msg": "success"
}
```

### Auth
- `POST /api/v1/auth/login`
- `GET /api/v1/inventory/test`

### Product & Batch
- `GET /api/v1/products`
  - 支持 `q` 模糊搜索：名称、条码、HB 编码
- `POST /api/v1/products`
  - 新建商品档案
- `POST /api/v1/inventory/inbound`
  - 接收 `hb_code` 或 `barcode`，以及 `batch_no`、`expiry_date`、`quantity`、`cost`
  - 若同商品同到期日批次已存在，则累加入库数量；否则创建新批次

## 前端页面
- `/login`：登录页
- `/products`：商品中心，包含搜索、总库存展示与商品建档
- `/inbound`：H5 优先入库流程
- `/`、`/outbound`、`/stock`：当前保留为工作台与后续阶段入口

## 本地运行

### 1. 安装后端依赖
```bash
python3 -m pip install -r backend/requirements.txt
```

### 2. 启动后端
```bash
python3 backend/app.py
```

默认服务地址：`http://127.0.0.1:5000`

默认管理员账号：
- 用户名：`admin`
- 密码：`Admin@123456`

### 3. 运行后端测试
```bash
python3 -m pytest backend/tests
```

### 4. 启动前端
```bash
cd frontend
npm install
npm run dev
```

默认前端地址：`http://127.0.0.1:5173`

开发环境下，Vite 会将 `/api` 代理到 `http://127.0.0.1:5000`。

## 验证结果
- `python3 -m pytest backend/tests` 通过
- `npm run build` 通过

## 后续方向
- FIFO 出库分配与批次扣减
- 库存明细、近效期预警、批次查询
- 更细粒度权限与操作日志
