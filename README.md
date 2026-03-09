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

### Stage 3
- 单位体系：`base_unit`、`purchase_unit`、`conversion_rate`
- 预占库存：`reserved_quantity`、FIFO 预占、可售库存计算
- 渠道映射：`ChannelMapping` 支持外部 SKU 与内部 `hb_code` 绑定
- 商品详情页与渠道映射管理页

### Stage 4
- CSV 数据导入：预览、确认保存、单位换算初始化
- 导入默认值：缺失 `expiry_date` 自动补成 `2099-12-31`
- 到期预警看板：已过期 / 临期 30 天 / 健康
- 到期报表：状态筛选、颜色标识、到期日升序批次列表

### Stage 5
- 订单闭环：渠道订单同步、FIFO 预占、发货核销、`OUT` 流水留痕
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
│   │   └── import_service.py
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
│           ├── DataManagementView.vue
│           ├── FinanceView.vue
│           ├── HomeView.vue
│           ├── InboundView.vue
│           ├── LoginView.vue
│           ├── OrdersView.vue
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

### Product & Inventory
- `GET /api/v1/products`
- `GET /api/v1/products/<hb_code>`
- `POST /api/v1/products`
- `POST /api/v1/inventory/inbound`
  - 接收 `unit_type`：`base` / `purchase`
  - `purchase` 会按 `quantity * conversion_rate` 转为最小单位入库
- `POST /api/v1/inventory/reserve`
  - 按 FIFO 顺序预占可售库存
  - 只增加 `reserved_quantity`，不减少 `current_quantity`
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
  - 通过 `ChannelMapping` 查找商品并按 FIFO 生成预占
- `POST /api/v1/orders/fulfill`
  - 接收 `order_id`
  - 将预占记录核销为真实出库，并减少 `current_quantity` 与 `reserved_quantity`

### Reports
- `GET /api/v1/reports/export`
  - 查询参数：`format=csv|xlsx`
  - 导出 `Product + Batch` 全量库存与批次数据
  - 仅 `admin` 可调用

### Channel Mapping
- `GET /api/v1/channel-mappings`
- `GET /api/v1/channel-mappings/lookup`
- `POST /api/v1/channel-mappings`
  - 仅 `admin` 可调用

## 前端页面
- `/login`：登录页
- `/`：首页保质期预警看板
- `/products`：商品中心
- `/products/:hbCode`：商品详情，包含预占库存和批次明细
- `/channels`：渠道映射管理
- `/data`：CSV 数据导入页，先预览后保存
- `/orders`：渠道订单列表，支持同步订单与发货核销
- `/finance`：财务统计入口，仅管理员可见
- `/inbound`：H5 优先入库流程，支持采购单位和最小单位切换
- `/settings`：用户设置入口，仅管理员可见
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

## 注意事项
- 当前项目仍未接入数据库迁移工具；如果你本地沿用旧版 SQLite 文件，新增字段不会自动补齐。开发中遇到旧 schema 冲突时，删除本地 `instance/roseate_wms.db` 后重新启动即可。
- CSV 导入假设商品档案已存在；导入阶段不会自动创建商品。

## 验证结果
- `python3 -m pytest backend/tests` 通过（15 tests）
- `npm run build` 通过
- 管理员报表导出已用 Flask test client 实测，`csv` 与 `xlsx` 都返回 `200`

## 后续方向
- 订单取消 / 预占释放
- 盘点、损耗、逆向退货流程
- 更细粒度的用户与权限管理
