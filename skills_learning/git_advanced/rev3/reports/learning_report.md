# 技能学习报告: git_advanced

| 属性 | 值 |
|------|-----|
| 版本 | rev3 |
| 评分 | 95/100 PASS |
| 案例数 | 6 条 |
| 模式总数 | 24 个 |
| 继承自 rev2 | 24 个 |
| 新增 | 0 个 |

## 知识模式

### 领域专有 (7个)
- [95%] Git Rebase 与 Merge 的高级策略：理解何时使用 Rebase 来保持线性历史，何时使用 Merge 保留分支上下文，以及交互式 Rebase 进行提交整理。
- [92%] Git 工作流模式与分支策略：深入理解 Git Flow、GitHub Flow、GitLab Flow 等模式，以及如何根据项目规模选择合适的分支策略。
- [90%] Git 高级调试与历史重写：使用 bisect 进行二分查找定位 bug，利用 filter-branch 或 git-filter-repo 清理敏感数据或重构历史。
- [88%] Git 钩子与自动化工作流：利用 pre-commit、pre-push 等钩子实现代码检查、测试自动化和部署触发，提升团队协作效率。
- [85%] Git 子模块与子树管理：掌握在大型项目中管理外部依赖和共享代码库的方法，包括子模块的添加、更新、冲突解决及子树合并。
- [70%] 在协作中优先使用变基而非合并来整合功能分支，以保持历史线性且易于追溯。
- [65%] 定期清理已合并或过时的分支，避免仓库历史杂乱，提升可维护性。

### 高级模式 (17个)
- [90%] 使用 CI/CD 自动化测试和部署
- [90%] 使用交互式变基（interactive rebase）来压缩、编辑或重新排序提交，以维护清晰、线性的项目历史。
- [90%] 掌握reflog以恢复误操作（如重置、变基或删除分支）丢失的提交，作为安全网。
- [88%] 使用 Git Flow 或 Trunk-Based 分支策略
- [87%] 解决合并冲突的策略和技巧
- [86%] PR/MR 代码审查流程
- [85%] 提交信息规范(Conventional Commits)
- [85%] 利用cherry-pick从其他分支选择性地应用特定提交，避免合并整个分支的变更。
- [85%] 使用git bisect通过二分查找快速定位引入缺陷的提交，提高调试效率。
- [84%] 使用 git hooks 自动化代码检查
- [83%] git tag 版本标记与发布管理
- [82%] 使用 rebase 保持提交历史整洁
- [82%] git stash 暂存未完成的工作
- [80%] cherry-pick 选择性合并特定提交
- [80%] 利用git worktree在同一仓库中同时检出多个分支，便于并行开发和测试。
- [78%] git bisect 二分查找引入 bug 的提交
- [76%] 子模块管理(submodule)多仓库项目

## 参考案例 (6条)

- wshobson/agents/git-advanced-workflows
- [Git](https://en.wikipedia.org/wiki/Git)
- [GIT quotient](https://en.wikipedia.org/wiki/GIT_quotient)
- [Linux kernel version history](https://en.wikipedia.org/wiki/Linux_kernel_version_history)
- [Alsamixer](https://en.wikipedia.org/wiki/Alsamixer)
- [Advanced Vector Extensions](https://en.wikipedia.org/wiki/Advanced_Vector_Extensions)