# 瑞幸咖啡

**注意，目前不支持配送，仅支持到店自取**

## 可用工具一览

共 8 个工具，分为三大类：

### 一、门店（1 个）

#### `queryShopList` — 查询门店列表

- **用途**：根据用户位置查询附近瑞幸门店
- **入参**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | `deptName` | string | 否 | 门店名称（模糊搜索） |
  | `longitude` | number | ✅ | 经度 |
  | `latitude` | number | ✅ | 纬度 |
- **响应关键字段**：`deptId`（门店ID）、`deptName`、`address`、`workTimeStart`/`workTimeEnd`（营业时间）、`distance`（距离，km）

---

### 二、商品（3 个）

#### `searchProductForMcp` — 搜索/推荐商品

- **用途**：根据用户自然语言描述，在指定门店匹配推荐商品
- **入参**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | `deptId` | integer | ✅ | 门店ID |
  | `query` | string | ✅ | 用户原始查询文本（如"生椰拿铁 少冰"） |
- **响应关键字段**：`productId`、`productName`、`skuCode`、`pictureUrl`、`productAttrs`（属性列表：温度/甜度/规格等）、
  `initialPrice`（面价）、`estimatePrice`（预估到手价）

#### `switchProduct` — 切换商品属性

- **用途**：修改商品的具体属性（如换杯型、加料、选甜度）
- **入参**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | `deptId` | integer | ✅ | 门店ID |
  | `productId` | integer | ✅ | 商品ID |
  | `skuCode` | string | ✅ | 商品SKU编码 |
  | `attrOperationParam.attributeId` | integer | ✅ | 属性组ID |
  | `attrOperationParam.subAttr.attributeId` | integer | ✅ | 属性值ID |
  | `attrOperationParam.subAttr.operation` | integer | ✅ | 操作类型（选中传 `3`） |
  | `amount` | integer | ✅ | 商品数量 |
- **响应**：返回切换后的完整商品信息（含更新后的 `skuCode`、`estimatePrice` 等）

#### `queryProductDetailInfo` — 查询商品详情

- **用途**：获取指定商品的完整属性信息
- **入参**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | `deptId` | integer | ✅ | 门店ID |
  | `productId` | integer | ✅ | 商品ID |
- **响应**：同商品搜索结果结构

---

### 三、订单（4 个）

#### `previewOrder` — 订单预览

- **用途**：下单前预览价格、优惠、预计取餐时间
- **入参**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | `deptId` | integer | ✅ | 门店ID |
  | `productList[].amount` | integer | ✅ | 数量 |
  | `productList[].productId` | integer | ✅ | 商品ID |
  | `productList[].skuCode` | string | ✅ | SKU编码 |
- **响应关键字段**：`aboutTime`（预计取餐时间戳）、`discountPrice`（实际付款价）、`shopInfo`、`productInfoList`

#### `createOrder` — 创建订单

- **用途**：正式提交订单，获取支付链接
- **入参**：
  | 参数 | 类型 | 必填 | 说明 |
  |------|------|------|------|
  | `deptId` | integer | ✅ | 门店ID |
  | `productList[]` | array | ✅ | 同上 |
  | `longitude` | number | ✅ | 经度 |
  | `latitude` | number | ✅ | 纬度 |
  | `couponCodeList` | array[string] | 否 | 优惠券编码 |
- **响应关键字段**：`orderId`、`payOrderUrl`（微信支付URL）、`payOrderQrCodeUrl`（支付二维码）、`discountPrice`、`needPay`

#### `queryOrderDetailInfo` — 查询订单详情

- **用途**：查看订单状态、取餐码、配送信息
- **入参**：`orderId`（string，必填）
- **订单状态码**：`10`=待付款 → `20`=下单成功 → `30`=制作中 → `60`=等待取餐 → `80`=已完成 → `100`=已取消
- **响应关键字段**：`orderStatus`、`takeMealCodeInfo.code`（取餐码）、`dispatchInfo`（配送员信息）

#### `cancelOrder` — 取消订单

- **用途**：取消未完成的订单
- **入参**：`orderId`（string，必填）
- **响应**：`data`（boolean，是否取消成功）

---

## 标准点单流程

请严格按以下顺序引导用户完成点单：

```
1. 获取位置 → queryShopList（需要用户提供经纬度）
2. 选择门店 → 用户确认门店，记录 deptId
3. 搜索商品 → searchProductForMcp（用户说想喝什么）
4. 调整属性 → switchProduct / queryProductDetailInfo（选规格/温度/甜度）
5. 预览订单 → previewOrder（确认价格与取餐时间）
6. 创建订单 → createOrder（返回支付链接/二维码）
7. 查询状态 → queryOrderDetailInfo（查看取餐码、制作进度）
```
---

## 行为准则

1. **位置优先**：每次操作前必须确认门店ID（`deptId`），没有门店无法进行后续操作。
2. **自然语言理解**：用户说"一杯少冰不加糖的生椰拿铁"时，先调用 `searchProductForMcp`，再根据返回的属性列表调用
   `switchProduct` 进行精确配置。
3. **价格透明**：在下单前必须调用 `previewOrder`，向用户展示预估到手价和预计取餐时间。
4. **支付引导**：`createOrder` 返回的 `payOrderUrl` 或 `payOrderQrCodeUrl` 需清晰展示给用户完成支付。
5. **状态追踪**：下单后主动提示用户可随时查询订单状态和取餐码。
6. **异常处理**：若门店不在营业时间、商品缺货、订单状态不允许取消等情况，需友好提示用户。

## 可能过时的数据，不优先考虑，备用

这份文档最后更新于 2026.6.20, 官方url: https://open.luckincoffee.com/docs 遇到冲突或者不符考虑参考该文档

根据测试，取餐二维码的生成没有官方api, 是 `queryOrderDetailInfo` 返回的 `takeMealCodeInfo` 字段下的 `takeOrderId`
直接生成的二维码
可以考虑构建 https://api.2dcode.biz/v1/create-qr-code?data= 的url发送给用户(data=后跟字符串，不需要引号)