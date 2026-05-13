# rocom_helper

真寻机器人的洛克王国助手插件

参考[astrbot_plugin_rocom](https://github.com/Entropy-Increase-Team/astrbot_plugin_rocom)插件实现

查询洛克王国远行商人今日排期、精灵图鉴、查蛋尺寸反查与玩家资料，支持图片渲染输出

## 使用

- 远行商人
- XX图鉴 (例：火花图鉴、迪莫图鉴)
- 洛克查蛋 0.18 1.5 (前一个参数为身高m，后一个参数为体重kg)
- 洛克查蛋 身高0.18m 体重1.5kg (带前缀写法)
- 查蛋 0.18 1.5 (洛克查蛋别名)
- 洛克玩家 <UID>

### 被动功能

- 远行商人定时推送（每日 8:05/12:05/16:05/20:05 自动推送到已开启该被动的群）

### 配置说明

<details>
<summary>API_BASE_URL</summary>

- 洛克王国后端 API 地址
- 默认值：https://wegame.shallow.ink
</details>
<details>
<summary>API_KEY</summary>

- WeGame API Key；默认使用参考仓库公开测试 key
- 默认值：sk-ff14f964051a5c966564e29b5bd3a768
</details>
<details>
<summary>WIKI_BASE_URL</summary>

- 洛克王国世界图鉴数据源地址；WeGame Wiki 接口不可用时使用
- 默认值：https://rocom.game-walkthrough.com
</details>

## 更新

**2026/5/13**[v0.7]

1. 初版