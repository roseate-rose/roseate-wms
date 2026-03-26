# Roseate-WMS

Roseate-WMS（蕴香和本轻量化仓库管理系统）面向美妆、医药等强批次管理场景，核心目标是围绕批次（Batch）和 FIFO 出库构建轻量、可扩展、移动优先的仓储系统。

## 当前完成范围

### Stage 1
- JWT 登录与受保护接口
- JWT 访问令牌有效期为 7 天
- Vue 3 + Vite + Tailwind 基础框架
- 全局路由守卫与 Axios Token 注入
- 桌面侧边栏 / 移动端底部导航响应式布局
- 用户设置页支持主动退出登录，管理员可查看系统用户清单

### Stage 2
- `Product` / `Batch` 批次化库存模型
- 商品中心：商品建档、模糊搜索、总库存聚合展示
- H5 入库流程：识别条码/内部编码、缺档引导、批次入库
- 入库合并逻辑：同一商品 + 相同到期日累加到同一批次

### Stage 3
- 单位体系：`base_unit`、`purchase_unit`、`conversion_rate`
- 预占库存：`reserved_quantity`、FIFO 预占、可售库存计算
- 渠道映射：`ChannelMapping` 支持外部 SKU 与内部 `hb_code` 绑定
- 商品详情页与渠道映射管理页
- 商品主档支持管理员在 UI 直接修正（更新 / 删除受限于关联数据）

### Stage 4
- CSV 数据导入：预览、确认保存、单位换算初始化
- 商品导入页内置标准表头说明与识别结果卡片，降低错列导入风险
- 导入默认值：缺失 `expiry_date` 自动补成 `2099-12-31`
- 到期预警看板：已过期 / 临期 30 天 / 健康
- 到期报表：状态筛选、颜色标识、到期日升序批次列表

### Stage 5
- 订单闭环：渠道订单同步、FIFO 预占、发货核销、`OUT` 流水留痕
- 订单导入当前仅开放微信小店标准导出模板，并在页面内展示关键映射、表头清单与 CSV 示例下载
- RBAC：`admin_required` 保护导入、导出、渠道映射写入等敏感接口
- 报表导出：管理员可下载商品 + 批次全量 CSV / Excel
- Web/H5 协同：订单列表、下载按钮、未知扫码快捷映射、按角色隐藏菜单

## 目录结构
```text
roseate-wms/
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── extensions.py
│   ├── models.py
│   ├── requirements.txt
│   ├── services/
│   │   ├── __init__.py
│   │   ├── import_service.py
│   │   ├── inbound_import_service.py
│   │   ├── order_import_service.py
│   │   └── product_import_service.py
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
│       ├── auth/session.js
│       ├── layouts/MainLayout.vue
│       ├── main.js
│       ├── router/index.js
│       ├── style.css
│       └── views/
│           ├── ChannelMappingsView.vue
│           ├── ChangelogView.vue
│           ├── DataManagementView.vue
│           ├── FinanceView.vue
│           ├── HomeView.vue
│           ├── InboundImportView.vue
│           ├── InboundView.vue
│           ├── LoginView.vue
│           ├── OtherView.vue
│           ├── OrdersView.vue
│           ├── OrdersImportView.vue
│           ├── OutboundView.vue
│           ├── ProductDetailView.vue
│           ├── ProductsView.vue
│           ├── SettingsView.vue
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
- 字段：`hb_code`, `barcode`, `name`, `spec`, `unit`, `base_unit`, `purchase_unit`, `conversion_rate`, `extra_data`
- 商品库存通过批次动态汇总：
  - `total_stock`
  - `reserved_stock`
  - `sellable_stock`

### `Batch`
- 字段：`id`, `hb_code`, `batch_no`, `production_date`, `expiry_date`, `cost`, `initial_quantity`, `current_quantity`, `reserved_quantity`, `extra_data`
- 入库合并键：`hb_code + expiry_date`
- FIFO 排序依据：`expiry_date` 升序
- 可售数量：`current_quantity - reserved_quantity`

### `ChannelMapping`
- 字段：`id`, `channel_name`, `external_sku_id`, `hb_code`, `extra_data`

### `SalesOrder`
- 字段：`id`, `channel_name`, `external_sku_id`, `hb_code`, `quantity`, `status`, `fulfilled_at`, `extra_data`
- 状态流转：`reserved -> fulfilled`

### `OrderAllocation`
- 字段：`id`, `order_id`, `batch_id`, `quantity`, `extra_data`
- 用途：记录订单跨批次的 FIFO 预占拆分结果

### `InventoryTransaction`
- 字段：`id`, `hb_code`, `batch_id`, `order_id`, `transaction_type`, `quantity`, `extra_data`
- 当前阶段用于发货时生成 `OUT` 流水

### `InboundReceipt` / `InboundLine`
- 用途：记录入库单据与入库明细行，给台账导出提供“单据编号”和可追溯的入库来源
- 关键字段：
  - `InboundReceipt.receipt_no`（入库单号）
  - `InboundLine.hb_code / batch_id / normalized_quantity / unit_cost`

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
  - 登录成功后返回 JWT；默认有效期 `7 days`
- `GET /api/v1/users`
  - 返回系统用户列表
  - 仅 `admin` 可调用
- `GET /api/v1/inventory/test`

### Product & Inventory
- `GET /api/v1/products`
- `GET /api/v1/products/<hb_code>`
- `POST /api/v1/products`
- `PUT /api/v1/products/<hb_code>`
  - 更新商品主档（`hb_code` 不可修改）
  - 仅 `admin` 可调用
- `DELETE /api/v1/products/<hb_code>`
  - 删除无关联库存/订单/流水/入库记录的商品主档
  - 仅 `admin` 可调用
- `POST /api/v1/products/import/preview`
  - `multipart/form-data`
  - 字段：`file`, `mode=skip|overwrite`
  - 必填列：`hb_code`, `name`, `spec`
  - 可选列：`barcode`, `unit`, `base_unit`, `purchase_unit`, `conversion_rate`, `extra_data`(JSON)
  - 支持常见中文表头别名（如 `HB编码`、`商品名称`、`计量单位`、`最小单位`、`采购单位`、`换算率`）
  - 会忽略纯空白的 `Unnamed:*` 尾随列，避免 `unit` 之后字段错位污染
  - 返回前 5 条预览数据
- `POST /api/v1/products/import`
  - `multipart/form-data`
  - 字段：`file`, `mode=skip|overwrite`
  - 仅 `admin` 可调用
- `POST /api/v1/inventory/inbound`
  - 接收 `unit_type`：`base` / `purchase`
  - `purchase` 会按 `quantity * conversion_rate` 转为最小单位入库
  - 可选传入 `receipt_no`（用于把多行入库归并到同一张入库单）
  - 会自动写入一条 `IN` 类型的 `InventoryTransaction`（用于台账与结存计算）
- `POST /api/v1/inventory/inbound-import/preview`
  - `multipart/form-data`
  - 字段：`file`, `mapping`(JSON，可选), `receipt_no`(可选), `supplier_name`(可选), `remark`(可选)
  - 支持 CSV / Excel。通过 `mapping` 将你的列名映射为系统字段（适配菜鸟/顺丰等模板）
  - 返回列名、有效映射、前 5 条预览和错误摘要
- `POST /api/v1/inventory/inbound-import`
  - `multipart/form-data`
  - 字段同 preview
  - 会生成入库单与明细行，并写入 `IN` 流水
  - 未映射列会写入 `line_extra_data.row_extra`，为未来接入物流/供应链 API 预留
- `POST /api/v1/inventory/reserve`
  - 按 FIFO 顺序预占可售库存
  - 只增加 `reserved_quantity`，不减少 `current_quantity`
  - 会创建一张 `manual` 订单记录，便于通过 `/orders/cancel` 释放预占
- `GET /api/v1/inventory/expiry-report`
  - 返回到期日升序批次明细
  - 支持 `status=expired|warning|healthy`

### Dashboard
- `GET /api/v1/dashboard/stats`
  - 返回：
    - `total_value`
    - `expired_count`
    - `warning_count`
    - `healthy_count`

### Import
- `POST /api/v1/inventory/import/preview`
  - `multipart/form-data`
  - 字段：`file`, `merge_mode`
  - 返回前 5 条预览数据
- `POST /api/v1/inventory/import`
  - `multipart/form-data`
  - 字段：`file`, `merge_mode`
  - 支持 `merge_mode=accumulate|overwrite`
  - CSV 需至少包含：`hb_code`, `quantity`
  - 可选列：`expiry_date`, `production_date`, `batch_no`, `cost`, `unit_type`
  - 若缺失 `expiry_date`，自动补为 `2099-12-31`
  - 仅 `admin` 可调用

### Orders
- `GET /api/v1/orders`
  - 返回订单列表，支持按 `status` 过滤
- `POST /api/v1/orders/sync`
  - 接收 `channel_name`, `external_sku_id`, `quantity`
  - 可选：`external_order_no`（外部订单号，用于幂等；建议真实 webhook 一律传入）
  - 通过 `ChannelMapping` 查找商品并按 FIFO 生成预占
- `POST /api/v1/orders/import/preview`
  - `multipart/form-data`
  - 字段：`file`, `mapping`(JSON，可选), `default_channel_name`(可选), `template`(可选)
  - 支持 `template=wechat_shop`，按提供的微信小店标准导出表头自动识别 `订单号` / `SKU编码(自定义)` / `商品编码(自定义)` / `商品数量`
  - 预览时会检查渠道映射是否存在，并对可售库存做粗略预估（产品级别）
- `POST /api/v1/orders/import`
  - `multipart/form-data`
  - 字段同 preview
  - 批量创建并预占订单；未映射列会写入订单 `extra_data.row_extra`，便于后续对接物流商 API
- `POST /api/v1/orders/fulfill`
  - 接收 `order_id`
  - 将预占记录核销为真实出库，并减少 `current_quantity` 与 `reserved_quantity`
  - 仅 `admin` 可调用
- `POST /api/v1/orders/cancel`
  - 接收 `order_id`
  - 释放该订单 allocations 中的 `reserved_quantity` 并将订单标记为 `cancelled`
  - `staff` 仅可取消 `manual` 预占；外部渠道订单取消需要 `admin`

### Reports
- `GET /api/v1/reports/export`
  - 查询参数：`format=csv|xlsx`
  - 导出 `Product + Batch` 全量库存与批次数据
  - 仅 `admin` 可调用
- `GET /api/v1/reports/ledger-export`
  - 查询参数：
    - `format=csv|xlsx`
    - `balance_scope=product|batch`（结存口径）
    - `include_batch=1`（可选：追加导出批次号和到期日列）
  - 导出出入库台账（参考模板表头），并计算运行中的结存数量
  - 仅 `admin` 可调用

### Channel Mapping
- `GET /api/v1/channel-mappings`
- `GET /api/v1/channel-mappings/lookup`
- `POST /api/v1/channel-mappings`
  - 仅 `admin` 可调用

## 前端页面
- `/login`：登录页
- `/`：首页保质期预警看板
- `/products`：商品中心，管理员可新建 / 编辑 / 删除商品主档，并在导入面板直接查看标准表头与识别结果
- `/products/:hbCode`：商品详情，包含预占库存和批次明细
- `/channels`：渠道映射管理
- `/data`：CSV 数据导入页，先预览后保存
- `/orders`：渠道订单列表，支持同步订单与发货核销
- `/orders-import`：批量订单导入（渠道为选项式入口，当前仅开放微信小店 CSV，并显示模板字段清单与 CSV 示例下载）
- `/finance`：财务统计入口，仅管理员可见
- `/inbound`：H5 优先入库流程，支持采购单位和最小单位切换
- `/inbound-import`：批量入库导入（生成入库单、入库明细与 IN 流水）
- `/settings`：用户设置入口，所有登录用户可见；支持退出登录，管理员额外可见系统用户列表
- `/stock`：到期报表页，支持状态筛选与红/黄/绿行背景
- `/outbound`：后续阶段入口

## 本地运行

### 1. 安装后端依赖
```bash
python3 -m pip install -r backend/requirements.txt
```

其中 `pandas` 与 `openpyxl` 用于 Stage 5 的 Excel/CSV 报表导出。

### 2. 启动后端
```bash
python3 backend/app.py
```

默认服务地址：`http://127.0.0.1:5000`

默认以稳定模式启动（不启用 Flask reloader）。如需调试与自动重载：

```bash
python3 backend/app.py --debug
```

如果本机 `5000` 端口被占用，可指定端口：

```bash
python3 backend/app.py --port 5001
```

默认管理员账号：
- 用户名：`admin`
- 密码：`Admin@123456`

默认员工账号：
- `warehouse / Warehouse@123456`（仓库专员，`staff`）
- `inbound / Inbound@123456`（入库专员，`staff`）
- `orders / Orders@123456`（订单专员，`staff`）

如需覆盖默认员工账号，可通过环境变量 `DEFAULT_EXTRA_USERS_JSON` 传入 JSON 数组。

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

如果后端端口不是 `5000`，可在启动前端时覆盖代理目标，例如后端在 `5001`：

```bash
cd frontend
VITE_API_PROXY_TARGET=http://127.0.0.1:5001 npm run dev
```

### 本地测试服务常驻启动

如果你希望本地“测试服务”一直在后台运行（关掉终端也不退出），可以使用脚本。

端口约定（请保持不变，便于跨项目工具对接）：
- 后端固定 `http://127.0.0.1:5001`
- 前端固定 `http://127.0.0.1:5174`

```bash
./scripts/local_test_up.sh
```

如果你更希望用一个可随时 attach 的常驻会话（推荐），用 `screen`：

```bash
./scripts/local_test_screen_up.sh
screen -r roseate-wms
```

可选环境变量：

- `BACKEND_PORT`：后端端口（默认 `5001`，不建议改）
- `FRONTEND_PORT`：前端端口（默认 `5174`，不建议改）
- `RUN_DIR`：pid/log 输出目录（默认 `instance/run`）

停止与查看状态：

```bash
./scripts/local_test_status.sh
./scripts/local_test_down.sh
```

如果端口被其他项目占用，我们不换端口，直接清理占用（需要显式确认）：

```bash
./scripts/local_test_kill_conflicts.sh
CONFIRM=1 ./scripts/local_test_kill_conflicts.sh
```

说明：

- 前端以 `--strictPort` 启动，端口被占用会直接退出，避免“悄悄换端口”导致外部测试连错地址。
- 后端优先用 `gunicorn`（如果已安装），否则 fallback 到 `python3 backend/app.py`。

## Docker 部署

项目根目录下提供了多阶段构建的 `Dockerfile`：

- 第一阶段在 `frontend/` 执行 `npm install` 和 `npm run build`
- 第二阶段在 `backend/` 安装 Python 依赖
- 最终运行阶段仅保留后端代码、已安装依赖和 `frontend/dist`
- 运行入口为 `gunicorn --bind 0.0.0.0:8000 backend.app:app`

### 构建镜像

```bash
docker build -t roseate-wms .
```

### 运行容器

```bash
docker run --rm -p 8000:8000 -v "$(pwd)/instance:/app/instance" roseate-wms
```

说明：

- Flask 会直接从容器内的 `frontend/dist` 提供静态资源
- Vue Router 的 History 路由会回退到 `index.html`
- `/api/...` 仍由 Flask API 处理，未知接口保持 JSON `404`
- SQLite 建议写入容器内 `/app/instance/wms.db`，并通过挂载卷持久化（Fly 部署已默认如此）

## Fly.io 部署

仓库根目录提供了 [fly.toml](/Users/paul/Work/roseate-wms/fly.toml)：

- 应用名：`roseate-wms`
- 容器内部服务端口：`8000`
- 默认区域：`sin`（新加坡，香港不可用时的最近区域）
- 机器规格：`shared-cpu-1x` / `256MB`
- 挂载卷：`roseate_storage -> /app/instance`
- 环境变量：`DATABASE_URL=sqlite:////app/instance/wms.db`

Fly 部署前需要先创建持久化卷，例如：

```bash
fly volumes create roseate_storage --size 1 --region sin
fly deploy
```

也可以直接使用根目录脚本：

```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会：

- 检查 `flyctl` 是否可用
- 检查 `roseate_storage` 是否已存在，不存在时自动创建
- 执行 `flyctl deploy --app roseate-wms --remote-only --depot=false`，避免 Depot 授权失败时中断部署

JWT 密钥需要单独通过 Fly secrets 配置，例如：

```bash
flyctl secrets set JWT_SECRET_KEY='replace-with-a-long-random-secret' --app roseate-wms
```

建议使用长度至少 32 字节的随机值。

## 注意事项
- 当前项目仍未接入数据库迁移工具；如果你本地沿用旧版 SQLite 文件，新增字段不会自动补齐。开发中遇到旧 schema 冲突时，可删除本地 `instance/wms.db`（或 `instance/roseate_wms.db`）后重新启动。
- `roseate-wms-webtest` 的 seed 默认写入 `instance/roseate_wms.db`；后端在未设置 `DATABASE_URL` 时会自动优先使用 `instance/` 下已存在的 SQLite 文件，避免 seed 后读到另一个库。
- `inventory/import`（批次库存导入）假设商品档案已存在；该导入不会自动创建商品。商品建档可使用 `products/import`（商品档案导入）。

## 验证结果
- `python3 -m pytest backend/tests` 通过（36 tests）
- `npm --prefix frontend run build` 通过
- 管理员报表导出已用 Flask test client 实测，`csv` 与 `xlsx` 都返回 `200`

## 后续方向
- 订单取消 / 预占释放
- 盘点、损耗、逆向退货流程
- 更细粒度的用户与权限管理
