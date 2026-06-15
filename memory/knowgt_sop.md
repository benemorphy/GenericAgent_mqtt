---
skill: knowgt
domain: web-scraping
version: "1.0"
tags: [github, trending, briefing, cdp]
---

# GitHub Trending 热榜简报 SOP

**来源**: https://fudankw.cn/sophub/sops/6a206ffedb64abbc9c1c3fb1
**核心**: 趋势解读，非爬虫维护

## 前置条件
- 浏览器tab可用作CDP导航（tmwebdriver）
- 模板文件: `temp/knowgt_template.html`（如无则纯md输出）

## 关键坑
1. **跨域导航必须用CDP Page.navigate**: `web_execute_js` 传 `{"cmd":"cdp","tabId":<id>,"method":"Page.navigate","params":{"url":"https://github.com/trending?since=daily"}}`。禁用`location.href`（页面卸载杀死上下文）。禁用fetch（15s硬限制）。
2. **Stars解析**: GitHub用逗号分隔（如`1,234`），需strip+replace
3. **SSL失败**: 首选tmwebdriver浏览器方案，不用requests/crawl4ai
4. **选择器可能变**: 定期验证BeautifulSoup选择器

## 7步流程
1. 确定范围: 默认daily，支持weekly/monthly
2. 获取数据: CDP导航→web_scan提取DOM→采集(仓库名/URL/语言/总stars/新增stars/描述)
3. 查找历史: 读`trending_reports/`最新2-5份
4. 对比分析: 🔥新上榜/⭐持续热门/📉掉出榜单
5. 撰写简报: 每个项目3句话(是什么/帮解决什么/谁需要)，禁术语
6. 保存输出: briefing+detailed双报告，不覆盖
7. HTML报告+打开: 模板渲染后`start`打开

## 输出目录
`trending_reports/trending_briefing_YYYY-MM-DD.{md,html}`
`trending_reports/trending_detailed_YYYY-MM-DD.md`
