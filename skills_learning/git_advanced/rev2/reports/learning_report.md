# 技能学习报告: git_advanced

| 属性 | 值 |
|------|-----|
| 版本 | rev2 |
| 评分 | 97/100 PASS |
| 案例数 | 21 条 |
| 模式总数 | 27 个 |
| 继承自 rev1 | 12 个 |
| 新增 | 15 个 |

## 知识模式

### 领域专有 (8个)
- [95%] Git Rebase 与 Merge 的高级策略：理解何时使用 Rebase 来保持线性历史，何时使用 Merge 保留分支上下文，以及交互式 Rebase 进行提交整理。
- [92%] Git 工作流模式与分支策略：深入理解 Git Flow、GitHub Flow、GitLab Flow 等模式，以及如何根据项目规模选择合适的分支策略。
- [90%] 保持主分支（如master）始终处于可部署状态，所有开发在特性分支上进行，通过Pull Request合并前确保代码稳定。
- [90%] Git 高级调试与历史重写：使用 bisect 进行二分查找定位 bug，利用 filter-branch 或 git-filter-repo 清理敏感数据或重构历史。
- [88%] 根据项目规模和协作需求选择合适的分支策略（如Git Flow、GitHub Flow、Forking工作流），开源项目推荐Forking工作流以隔离贡献者仓库。
- [88%] Git 钩子与自动化工作流：利用 pre-commit、pre-push 等钩子实现代码检查、测试自动化和部署触发，提升团队协作效率。
- [85%] Git 子模块与子树管理：掌握在大型项目中管理外部依赖和共享代码库的方法，包括子模块的添加、更新、冲突解决及子树合并。
- [82%] 及时合并特性分支到主分支，避免长期分支导致冲突累积，保持集成频率高。

### 高级模式 (19个)
- [90%] 使用 CI/CD 自动化测试和部署
- [88%] 使用 Git Flow 或 Trunk-Based 分支策略
- [87%] 解决合并冲突的策略和技巧
- [86%] PR/MR 代码审查流程
- [85%] 提交信息规范(Conventional Commits)
- [85%] 使用交互式rebase（interactive rebase）整理提交历史，在合并到主分支前压缩、重排或修改提交，以维护清晰线性的历史。
- [85%] 在合并分支时，优先使用rebase保持线性历史（适用于个人或私有分支），而merge保留上下文（适用于公共分支或协作场景），避免在共享分支上rebase。
- [84%] 使用 git hooks 自动化代码检查
- [83%] git tag 版本标记与发布管理
- [82%] 使用 rebase 保持提交历史整洁
- [82%] git stash 暂存未完成的工作
- [80%] cherry-pick 选择性合并特定提交
- [80%] 利用cherry-pick选择性地将特定提交应用到其他分支，避免合并整个分支，适用于修复补丁或功能移植。
- [80%] 掌握reflog（引用日志）以恢复误操作（如丢失的提交或分支），作为安全网应对意外情况。
- [78%] git bisect 二分查找引入 bug 的提交
- [76%] 子模块管理(submodule)多仓库项目
- [75%] 使用git bisect进行二分查找，快速定位引入bug的提交，提高调试效率。
- [75%] 在解决合并冲突时，使用图形化工具或手动编辑，确保冲突解决后测试通过，并优先使用merge而非rebase处理公共分支冲突。
- [70%] 利用git worktree同时检出多个分支的工作目录，便于并行开发或测试不同分支，无需频繁切换。

## 参考案例 (21条)

- wshobson/agents/git-advanced-workflows
- [Why branching strategies matter](https://graphite.dev/guides/advanced-git-branching-strategies)
- [Mastering Git for Efficient Version Control](https://codabase.io/4701/21-ways-to-master-version-control-with-git/)
- [Demystifying Advanced Git Commands: A Simple Guide](https://dev.to/ak_23/branching-strategy-guide-24d6)
- [几种常用的 Git 分支策略](https://developer.aliyun.com/article/1608451)
- [深入掌握Git分支管理的核心技巧](https://juejin.cn/post/7472334642974195724)
- [Git高级工作流：Rebase与Merge的正确使用场景解析](https://www.cnblogs.com/dblens/p/19566698)
- [Git Merge 与 Rebase 的区别及合并建议](https://juejin.cn/post/7457572013168492571)
- [Git Rebase和Merge](https://www.cnblogs.com/xyfhsy/p/17975361)
- [Git Rebase vs Git Merge: A Comprehensive Guide](https://arifszn.com/blog/git-rebase-vs-git-merge-a-comprehensive-guide)