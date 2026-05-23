# Aesthetic Design SOP - 通用审美设计技能

> 来源: skills.sh/anthropics/skills/frontend-design + canvas-design + theme-factory + brand-guidelines
>        + skills.sh/vercel-labs/agent-skills/web-design-guidelines
>        + Datawhale 前端设计 SOP + Vercel React Best Practices

## 1. 设计哲学 (Design Philosophy)

编码前确立大胆的美学方向，拒绝 AI 俗套：
- 拒绝: 紫蓝渐变、Inter/Roboto 字体、通用毛玻璃、居中对称布局
- 选择极端美学方向之一:
   粗野主义 | 极繁装饰 | 复古未来 | 有机自然 | 杂志风
   柔和粉彩 | 工业实用 | 几何精确 | 纸张纹理 | 科技深色
- **记忆点**: 用户能记住这个界面哪个特征？

## 2. Canvas 设计哲学 (canvas-design)

创建 VISUAL PHILOSOPHY，而非模板布局：
- 形式、空间、色彩、构图 四个维度设计
- 每个设计观点只提一次，不重复
- 文字始终最少化、视觉优先
- 追求博物馆/杂志级品质
- 理念应让熟悉主题的人直觉感受到，其他人体验到精妙

## 3. 色彩系统 (Color)

| 原则 | 说明 |
|------|------|
| 主导色+强调色 | 一个主色 + 一个锐利强调色，胜过均匀低对比调色板 |
| CSS 变量管理 | `--primary`, `--accent`, `--bg`, `--text` 等 |
| 亮/暗双主题 | 全面支持 light + dark mode |
| WCAG AA | 小文字 >=4.5:1，大文字 >=3:1 |
| 品牌色 | 使用品牌特定色板 |

theme-factory 推荐 10 套预设主题方向:
  海洋深蓝 | 日落大道 | 森林绿 | 现代极简 | 金色时刻
  北极霜 | 沙漠玫瑰 | 科技创新 | 暗夜紫 | 樱花粉

## 4. 字体排版 (Typography)

| 层级 | 字体 | 大小 | 说明 |
|------|------|------|------|
| Hero 标题 | 展示字体 | 32-48px | 独特、有冲击力 |
| 页面标题 | 衬线/无衬线 | 24-28px | 品牌一致性 |
| 小标题 | 与标题配对 | 18-20px | 区分层级 |
| 正文 | 易读字体 | 15-16px | line-height 1.6+ |
| 代码/数据 | 等宽字体 | 13-14px | JetBrains Mono / Fira Code |
| 标签/注释 | 辅助 | 12-13px | 最小可读尺寸 |

避免: Inter, Arial, Roboto, 系统默认字体

## 5. 布局 (Layout)

- 意想不到的布局: 不对称、重叠、打破网格
- 慷慨留白或控制密集，不要平庸均匀分布
- 使用卡片/网格/列表恰当组织
- 响应式移动优先: 320px -> 768px -> 1024px -> 1440px
- 毛玻璃导航: sticky + backdrop-filter + blur
- 卡片 hover: 上浮 + shadow + 缩放微动效

## 6. 动效 (Motion)

- 优先 CSS-only: transition/animation/keyframes
- 微交互: hover反馈、页面过渡、加载骨架
- 性能: 只使用 transform/opacity，避免 layout 触发
- 不要过度喧闹的动画

## 7. 可访问性 (Accessibility)

- 语义化 HTML: h1-h6, nav, main, section, article, aside
- 键盘导航可见焦点 (focus-visible)
- aria-label 补充图标/按钮含义
- 不要仅用颜色传达信息
- WCAG AA 色彩对比度 >=4.5:1

## 8. 实现原则

- 实现复杂度匹配美学愿景: 极繁=复杂代码，极简=精炼代码
- 生成真正可工作的代码(HTML/CSS/JS/React)
- 使用现代CSS: flexbox, grid, custom properties, container queries
- 不要在组件内定义组件 (React)
- useMemo/useCallback 缓存昂贵计算

## 9. 品牌指南 (brand-guidelines 适用时)

当需要品牌风格时应用:
- 标题 (24pt+): 品牌字体 (如 Poppins)
- 正文: 衬线字体 (如 Lora)
- 后备字体: Arial/Georgia
- 非文本形状使用强调色
- RGB 精确颜色确保跨系统一致

## 10. 审查清单 (每次 UI 提交前)

- [ ] 有清晰的美学方向吗? 拒绝 AI 俗套了吗?
- [ ] 字体有特色吗? 避免 Inter/Arial/Roboto 了吗?
- [ ] 配色避免紫蓝渐变了吗?
- [ ] 支持 light + dark 双主题?
- [ ] 响应式适配 (320px-1440px)?
- [ ] WCAG AA 色彩对比度达标?
- [ ] 有微交互动效 (hover/transition)?
- [ ] 代码完整可工作? 不是看起来差不多?
- [ ] 有一个让人记住的视觉特征?

## 11. 工具链

| 工具 | 用途 |
|------|------|
| Google Fonts | 独特字体选择 |
| CSS custom properties | 主题变量管理 |
| CSS Grid/Flexbox | 响应式布局 |
| backdrop-filter | 毛玻璃效果 |
| Canvas 2D API | 图形/图表/数据可视化 |
| p5.js | 生成式艺术/算法视觉 (algorithmic-art) |